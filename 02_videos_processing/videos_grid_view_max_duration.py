import subprocess
from pathlib import Path
import re
import os
import unicodedata
import tempfile
import math


# =========================
# Filename Sanitizer
# =========================
class FolderSanitizer:
    MAX_FILENAME_LENGTH = 50

    @staticmethod
    def sanitize_filename(name: str) -> str:
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
        name = re.sub(r"[^a-zA-Z0-9\-_.]+", "_", name)
        name = re.sub(r"_+", "_", name).strip("_.")
        base, ext = Path(name).stem, Path(name).suffix
        if len(base + ext) > FolderSanitizer.MAX_FILENAME_LENGTH:
            base = base[: FolderSanitizer.MAX_FILENAME_LENGTH - len(ext)]
        return f"{base or 'file'}{ext}"

    @classmethod
    def sanitize_folder(cls, folder: str):
        p = Path(folder)
        if not p.is_dir():
            raise ValueError(f"Folder not found: {folder}")

        files = sorted(f for f in p.iterdir() if f.is_file())
        existing = {f.name for f in files}
        out = []

        for f in files:
            name = cls.sanitize_filename(f.name)
            base, ext = Path(name).stem, Path(name).suffix
            i = 1
            while name in existing:
                suf = f"_{i}"
                name = f"{base[:cls.MAX_FILENAME_LENGTH-len(suf)-len(ext)]}{suf}{ext}"
                i += 1
            new = p / name
            if f != new:
                f.replace(new)
            existing.add(name)
            out.append(new)
        return out


# =========================
# Video Grid Creator
# =========================
class VideosGridView:
    # End behaviors
    FREEZE = 1
    LOOP = 2
    FADE_VIDEO = 3
    FADE_AUDIO = 4

    @staticmethod
    def _norm(v):
        return int(v[0] if isinstance(v, (tuple, list)) else v)

    @staticmethod
    def audio_duration(v: Path) -> float:
        try:
            r = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-select_streams", "a:0",
                    "-show_entries", "stream=duration",
                    "-of", "default=nw=1:nk=1",
                    str(v)
                ],
                capture_output=True, text=True, check=True
            )
            return float(r.stdout.strip() or 0)
        except Exception:
            return 0.0

    def max_audio_video(self, videos):
        valid = [(v, self.audio_duration(v)) for v in videos]
        valid = [(v, d) for v, d in valid if d > 0]
        return max(valid, key=lambda x: x[1])[0] if valid else None

    def max_audio_duration(self, videos):
        durs = [self.audio_duration(v) for v in videos if self.audio_duration(v) > 0]
        if not durs:
            raise ValueError("No audio tracks found")
        return max(durs)

    # =========================
    # Prepare videos according to end_behavior
    # =========================
    def prepare_videos(self, videos, duration, tmp, behavior):
        out = []

        for i, v in enumerate(videos):
            dst = Path(tmp) / f"prep_{behavior}_{os.getpid()}_{i}.mp4"

            if behavior == self.FREEZE:
                cmd = [
                    "ffmpeg", "-i", str(v),
                    "-vf", f"tpad=stop_mode=clone:stop_duration={duration}",
                    "-t", str(duration)
                ]
            elif behavior == self.LOOP:
                cmd = [
                    "ffmpeg", "-stream_loop", "-1",
                    "-i", str(v),
                    "-t", str(duration)
                ]
            elif behavior == self.FADE_VIDEO:
                st = max(duration - 1.0, 0)
                cmd = [
                    "ffmpeg", "-stream_loop", "-1",
                    "-i", str(v),
                    "-vf", f"fade=t=out:st={st}:d=1",
                    "-t", str(duration)
                ]
            else:
                raise ValueError("Invalid video behavior")

            cmd += [
                "-an",
                "-pix_fmt", "yuv420p",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-y", str(dst)
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            out.append(dst)

        return out

    # =========================
    # Compute grid: always 4x3
    # =========================

    def compute_grid(self, n):
        """
        Compute a grid layout (rows, cols) for n videos.
        - Up to 3 columns
        - Prefer square layouts when possible (e.g. 4 → 2x2)
        """
        if n <= 0:
            return 0, 0

        # Special case: perfect square <= 9
        root = int(math.sqrt(n))
        if root * root == n and root <= 3:
            return root, root

        # Default behavior
        cols = min(3, math.ceil(math.sqrt(n)))
        rows = math.ceil(n / cols)

        return rows, cols



    # =========================
    # Create grid batch
    # =========================
    def _grid_batch(self, videos, w, h, tmp, behavior):
        w, h = self._norm(w), self._norm(h)
        duration = self.max_audio_duration(videos)
        videos = self.prepare_videos(videos, duration, tmp, behavior)

        rows, cols = self.compute_grid(len(videos))
        cw, ch = w // cols, h // rows

        bg = Path(tmp) / f"bg_{os.getpid()}.mp4"
        subprocess.run(
            [
                "ffmpeg", "-f", "lavfi",
                "-i", f"color=size={w}x{h}:color=black:duration={duration}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-y", str(bg)
            ],
            capture_output=True, text=True, check=True
        )

        inputs = [str(bg)] + [str(v) for v in videos]
        filters = []
        last = "[0:v]"

        for i in range(1, len(videos) + 1):
            r, c = divmod(i - 1, cols)
            x, y = c * cw, r * ch
            # Crop to fill cell (no black bars)
            filters.append(
                f"[{i}:v]scale=w={cw}:h={ch}:force_original_aspect_ratio=increase,"
                f"crop={cw}:{ch}[v{i}];"
                f"{last}[v{i}]overlay={x}:{y}[t{i}]"
            )
            last = f"[t{i}]"

        out = Path(tmp) / f"grid_{os.getpid()}.mp4"
        cmd = ["ffmpeg"]
        for i in inputs:
            cmd += ["-i", i]
        cmd += [
            "-filter_complex", ";".join(filters),
            "-map", last,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-y", str(out)
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return out

    # =========================
    # Public API
    # =========================
    def create_video(
        self,
        canvas_width,
        canvas_height,
        input_folder,
        output_folder,
        end_behavior=LOOP,  # DEFAULT: LOOP
    ):
        w, h = self._norm(canvas_width), self._norm(canvas_height)

        videos = FolderSanitizer.sanitize_folder(input_folder)
        if not videos:
            raise ValueError("No videos found in folder!")

        audio_src = self.max_audio_video(videos)

        outp = Path(output_folder)
        outp.mkdir(parents=True, exist_ok=True)
        final = outp / videos[0].name

        tmp = Path(tempfile.mkdtemp())
        try:
            grid = self._grid_batch(videos, w, h, tmp, end_behavior)

            if audio_src:
                cmd = [
                    "ffmpeg",
                    "-i", str(grid),
                    "-i", str(audio_src),
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
                ]

                if end_behavior == self.FADE_AUDIO:
                    ad = self.audio_duration(audio_src)
                    st = max(ad - 1.0, 0)
                    cmd += ["-af", f"afade=t=out:st={st}:d=1"]

                cmd += ["-y", str(final)]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
            else:
                grid.replace(final)

            return final

        finally:
            for f in tmp.iterdir():
                f.unlink(missing_ok=True)
            tmp.rmdir()


# =========================
# Run
# =========================
if __name__ == "__main__":
    vg = VideosGridView()
    vg.create_video(
        canvas_width=1080,
        canvas_height=1920,
        input_folder="videos_processing/inputs/videos",
        output_folder="videos_processing/outputs",
        #end_behavior=VideosGridView.FREEZE  # Optional, default = LOOP
    )
    print("Done!")

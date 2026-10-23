import subprocess
from pathlib import Path
import re
import os
import unicodedata
import tempfile


class FolderSanitizer:
    MAX_FILENAME_LENGTH = 50

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
        sanitized = re.sub(r'[^a-zA-Z0-9\-_.]+', '_', filename)
        sanitized = re.sub(r'_+', '_', sanitized).strip("_.")
        base, ext = Path(sanitized).stem, Path(sanitized).suffix
        if len(base + ext) > FolderSanitizer.MAX_FILENAME_LENGTH:
            base = base[:FolderSanitizer.MAX_FILENAME_LENGTH - len(ext)]
        sanitized = f"{base}{ext}"
        return sanitized or "file"

    @classmethod
    def sanitize_folder(cls, folder: str):
        folder_path = Path(folder)
        if not folder_path.exists() or not folder_path.is_dir():
            raise ValueError(f"Folder does not exist: {folder}")

        existing_names = set(f.name for f in folder_path.iterdir() if f.is_file())
        sanitized_files = []

        for f in folder_path.iterdir():
            if not f.is_file():
                continue

            new_name = cls.sanitize_filename(f.name)
            counter = 1
            base, ext = Path(new_name).stem, Path(new_name).suffix

            while new_name in existing_names:
                suffix = f"_{counter}"
                trim_len = cls.MAX_FILENAME_LENGTH - len(suffix) - len(ext)
                new_name = f"{base[:trim_len]}{suffix}{ext}"
                counter += 1

            new_path = folder_path / new_name
            if f != new_path:
                try:
                    f.rename(new_path)
                    existing_names.add(new_name)
                except Exception as e:
                    print(f"Failed to rename {f.name}: {e}")

            sanitized_files.append(new_path)

        return sorted(sanitized_files)


class VideosGridView:
    def __init__(self):
        self.sanitizer = FolderSanitizer()

    @staticmethod
    def _normalize_dim(value):
        if isinstance(value, (tuple, list)):
            return int(value[0])
        return int(value)

    @staticmethod
    def has_audio(video_path: Path) -> bool:
        try:
            result = subprocess.run(
                ["ffprobe", "-i", str(video_path), "-show_streams",
                 "-select_streams", "a", "-loglevel", "error"],
                capture_output=True,
                text=True
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    @staticmethod
    def get_video_duration(video_path: Path) -> float:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error",
                 "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1",
                 str(video_path)],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def compute_grid(self, num_videos):
        if num_videos <= 1:
            return 1, 1
        elif num_videos <= 4:
            return 2, 2
        elif num_videos == 6:
            return 2, 3
        elif num_videos <= 9:
            return 3, 3
        elif num_videos <= 12:
            return 3, 4
        else:
            raise ValueError("Supports max 12 videos only")

    def _compute_grid_positions(self, num_videos, canvas_width, canvas_height):
        canvas_width = self._normalize_dim(canvas_width)
        canvas_height = self._normalize_dim(canvas_height)

        rows, cols = self.compute_grid(num_videos)
        cell_width = canvas_width // cols

        if num_videos == 6:
            cell_height = canvas_height // 2
            y_offsets = [0, cell_height]
        else:
            cell_height = canvas_height // rows
            y_offsets = [r * cell_height for r in range(rows)]

        return rows, cols, cell_width, cell_height, y_offsets

    def _grid_batch(self, videos, canvas_width, canvas_height, temp_dir):
        canvas_width = self._normalize_dim(canvas_width)
        canvas_height = self._normalize_dim(canvas_height)

        num_videos = len(videos)
        rows, cols, cell_width, cell_height, y_offsets = self._compute_grid_positions(
            num_videos, canvas_width, canvas_height
        )

        max_duration = max(self.get_video_duration(v) for v in videos)

        bg_file = Path(temp_dir) / "bg.mp4"
        subprocess.run(
            [
                "ffmpeg", "-f", "lavfi",
                "-i", f"color=size={canvas_width}x{canvas_height}:color=black:duration={max_duration}",
                "-c:v", "libx264",
                "-t", str(max_duration),
                "-pix_fmt", "yuv420p",
                "-y", str(bg_file)
            ],
            check=True,
            capture_output=True,
            text=True
        )

        inputs = [str(bg_file)] + [str(v) for v in videos]
        filter_cmds = []
        last_label = "[0:v]"

        for idx, _ in enumerate(videos, start=1):
            row = (idx - 1) // cols
            col = (idx - 1) % cols
            x = col * cell_width
            y = y_offsets[row]

            filter_cmds.append(
                f"[{idx}:v]scale=w={cell_width}:h={cell_height}:force_original_aspect_ratio=decrease,"
                f"pad={cell_width}:{cell_height}:(ow-iw)/2:(oh-ih)/2:color=black[v{idx}];"
                f"{last_label}[v{idx}]overlay={x}:{y}:shortest=1[tmp{idx}]"
            )
            last_label = f"[tmp{idx}]"

        filter_complex = ";".join(filter_cmds)
        output_file = Path(temp_dir) / f"grid_{os.getpid()}_{len(videos)}.mp4"

        cmd = ["ffmpeg"]
        for f in inputs:
            cmd.extend(["-i", f])

        cmd.extend(
            [
                "-filter_complex", filter_complex,
                "-map", last_label,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-y", str(output_file)
            ]
        )

        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return output_file

    def create_video(self, canvas_width, canvas_height, input_folder, output_folder):
        canvas_width = self._normalize_dim(canvas_width)
        canvas_height = self._normalize_dim(canvas_height)

        input_path = Path(input_folder)
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        videos = self.sanitizer.sanitize_folder(input_path)
        if not videos:
            raise ValueError("No videos found in input folder!")

        first_video = videos[0]
        final_output = output_path / first_video.name

        temp_dir = Path(tempfile.mkdtemp())
        temp_files = []

        try:
            batch_size = 12
            for i in range(0, len(videos), batch_size):
                batch = videos[i:i + batch_size]
                temp_files.append(
                    self._grid_batch(batch, canvas_width, canvas_height, temp_dir)
                )

            while len(temp_files) > 1:
                new_temp_files = []
                for i in range(0, len(temp_files), batch_size):
                    batch = temp_files[i:i + batch_size]
                    new_temp_files.append(
                        self._grid_batch(batch, canvas_width, canvas_height, temp_dir)
                    )
                for f in temp_files:
                    f.unlink(missing_ok=True)
                temp_files = new_temp_files

            stacked_video = temp_files[0]

            if self.has_audio(first_video):
                subprocess.run(
                    [
                        "ffmpeg",
                        "-i", str(stacked_video),
                        "-i", str(first_video),
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-map", "0:v",
                        "-map", "1:a",
                        "-shortest",
                        "-y", str(final_output)
                    ],
                    check=True,
                    capture_output=True,
                    text=True
                )
            else:
                stacked_video.rename(final_output)

            print("Final video saved:", final_output)
            return final_output

        finally:
            for f in temp_dir.iterdir():
                f.unlink(missing_ok=True)
            temp_dir.rmdir()


if __name__ == "__main__":
    vg = VideosGridView()
    final_video = vg.create_video(
        canvas_width=1080,
        canvas_height=1920,
        input_folder="videos_processing/inputs/videos",
        output_folder="videos_processing/outputs"
    )
    print("Done! Video saved at:", final_video)

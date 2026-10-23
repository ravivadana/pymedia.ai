import subprocess
from pathlib import Path


class SequentialGridVideoPipeline:
    def __init__(
        self,
        input_file,
        segments,
        output_folder,
        middle_image,
        middle_video,
        width=1080,
        height=1920,
        grid_midle_height=650,
        image_midle_sec=None,
        shift_up=50,  # NEW: pixels to move clip2 up
    ):
        self.input_file = Path(input_file)
        self.segments = segments
        self.output_folder = Path(output_folder)
        self.middle_image = Path(middle_image)
        self.middle_video = Path(middle_video)

        self.width = width
        self.height = height
        self.grid_midle_height = grid_midle_height
        self.panel_height = (self.height - grid_midle_height) // 2
        self.image_midle_sec = image_midle_sec
        self.shift_up = shift_up

        for f in [self.input_file, self.middle_image, self.middle_video]:
            if not f.exists():
                raise FileNotFoundError(f"File not found: {f}")

        self.output_folder.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, check=True)

    # -----------------------------
    # Split clips
    # -----------------------------
    def split_clips(self):
        for i, (start, end) in enumerate(self.segments, start=1):
            out = self.output_folder / f"clip{i}.mp4"
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", str(self.input_file),
                "-t", str(end - start),
                "-map", "0:v",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-crf", "23",
                "-preset", "fast",
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                "-movflags", "+faststart",
                str(out)
            ], check=True)

    # -----------------------------
    # Extract preview images
    # -----------------------------
    def extract_images(self):
        for i in (1, 2):
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", "0.3",
                "-i", str(self.output_folder / f"clip{i}.mp4"),
                "-vframes", "1",
                "-q:v", "2",
                str(self.output_folder / f"clip{i}.jpg")
            ], check=True)

    # -----------------------------
    # Grid segments
    # -----------------------------
    def create_grid_segments(self):
        shift_up = self.shift_up

        # SEGMENT 1
        filter_stack_seg1 = (
            f"[0:v]scale={self.width}:{self.panel_height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.panel_height}[top];"
            f"[1:v]scale={self.width}:{self.panel_height + shift_up}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.panel_height}:0:{shift_up}[bot];"
            f"[2:v]scale={self.width}:{self.grid_midle_height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.grid_midle_height}[mid];"
            f"[top][mid][bot]vstack=inputs=3"
        )

        seg1 = self.output_folder / "seg1.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(self.output_folder / "clip1.mp4"),
            "-loop", "1", "-i", str(self.output_folder / "clip2.jpg"),
            "-loop", "1", "-i", str(self.middle_image),
            "-filter_complex", filter_stack_seg1,
            "-map", "0:a?",
            "-shortest",
            "-c:v", "libx264",
            "-c:a", "aac",
            str(seg1)
        ], check=True)

        # SEGMENT 2
        filter_stack_seg2 = (
            f"[0:v]scale={self.width}:{self.panel_height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.panel_height}[top];"
            f"[1:v]scale={self.width}:{self.panel_height + shift_up}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.panel_height}:0:{shift_up}[bot];"
            f"[2:v]scale={self.width}:{self.grid_midle_height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.grid_midle_height}[mid];"
            f"[top][mid][bot]vstack=inputs=3"
        )

        seg2 = self.output_folder / "seg2.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(self.output_folder / "clip1.jpg"),
            "-i", str(self.output_folder / "clip2.mp4"),
            "-loop", "1", "-i", str(self.middle_image),
            "-filter_complex", filter_stack_seg2,
            "-map", "1:a?",
            "-shortest",
            "-c:v", "libx264",
            "-c:a", "aac",
            str(seg2)
        ], check=True)

        return seg1, seg2

    # -----------------------------
    # Middle overlay section
    # -----------------------------
    def create_middle_overlay(self):
        shift_up = self.shift_up
        out = self.output_folder / "middle_overlay.mp4"

        filter_complex = (
            # TOP
            f"[0:v]setsar=1,scale={self.width}:{self.panel_height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.panel_height}[top];"

            # BOTTOM (clip2 shifted up)
            f"[1:v]setsar=1,scale={self.width}:{self.panel_height + shift_up}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.panel_height}:0:{shift_up}[bot];"

            # MIDDLE IMAGE BACKGROUND
            f"[2:v]setsar=1,scale={self.width}:{self.grid_midle_height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.grid_midle_height}[bg];"

            # MIDDLE VIDEO FOREGROUND
            f"[3:v]setsar=1,scale={self.width}:{self.grid_midle_height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.grid_midle_height}[fg];"

            # OVERLAY MIDDLE VIDEO ON BACKGROUND
            f"[bg][fg]overlay=0:0[tmp];"

            # STACK TOP-MIDDLE-BOTTOM
            f"[top][tmp][bot]vstack=inputs=3"
        )

        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(self.output_folder / "clip1.jpg"),
            "-loop", "1", "-i", str(self.output_folder / "clip2.jpg"),
            "-loop", "1", "-i", str(self.middle_image),
            "-i", str(self.middle_video),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-filter_complex", filter_complex,
            "-shortest",
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "fast",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(out)
        ], check=True)

        return out

    # -----------------------------
    # Concat
    # -----------------------------
    def concat_all(self, seg1, mid, seg2):
        concat = self.output_folder / "concat.txt"
        concat.write_text(
            f"file '{seg1.resolve()}'\n"
            f"file '{mid.resolve()}'\n"
            f"file '{seg2.resolve()}'\n"
        )

        out = self.output_folder / "final_1080x1920.mp4"

        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(out)
        ], check=True)

        # Clean up intermediate files
        for f in self.output_folder.glob("*"):
            if f != out:
                f.unlink()

        print(f"✅ Final output → {out}")

    # -----------------------------
    # Run
    # -----------------------------
    def run(self):
        self.split_clips()
        self.extract_images()
        seg1, seg2 = self.create_grid_segments()
        middle = self.create_middle_overlay()
        self.concat_all(seg1, middle, seg2)


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    pipeline = SequentialGridVideoPipeline(
        input_file="videos_processing/inputs/videos/4.mp4",
        segments=[(0, 5), (7, 10)],
        output_folder="videos_processing/outputs/4_segments_grid",
        middle_image="videos_processing/inputs/images/bramhi_listening.jpg",
        middle_video="videos_processing/inputs/template/adi_idikadu.mp4",
        width=1080,
        height=1920,
        grid_midle_height=650,
        shift_up=50  # Adjust how much clip2 moves up
    )

    pipeline.run()

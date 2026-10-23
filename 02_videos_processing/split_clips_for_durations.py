import subprocess
from pathlib import Path


class SequentialGridVideoPipeline:
    def __init__(self, input_file, segments, output_folder, mobile_width=720, gap_height=60):
        self.input_file = Path(input_file)
        self.segments = segments
        self.output_folder = Path(output_folder)
        self.mobile_width = mobile_width
        self.gap_height = gap_height

        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

        self.output_folder.mkdir(parents=True, exist_ok=True)

        # Check ffmpeg
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, check=True)

    # -----------------------
    # Split video/audio
    # -----------------------
    def split_video_audio(self):
        for i, (start, end) in enumerate(self.segments, start=1):
            if end <= start:
                raise ValueError(f"Invalid segment: ({start}, {end})")

            duration = end - start
            video_file = self.output_folder / f"{i}.mp4"
            audio_file = self.output_folder / f"{i}.mp3"

            subprocess.run([
                "ffmpeg", "-y",
                "-ss", f"{start:.3f}", "-i", str(self.input_file),
                "-t", f"{duration:.3f}",
                "-an",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-movflags", "+faststart",
                str(video_file)
            ], check=True)

            subprocess.run([
                "ffmpeg", "-y",
                "-ss", f"{start:.3f}", "-i", str(self.input_file),
                "-t", f"{duration:.3f}",
                "-vn",
                "-c:a", "libmp3lame",
                str(audio_file)
            ], check=True)

            print(f"✅ Segment {i} split")

    # -----------------------
    # Merge video/audio
    # -----------------------
    def merge_clips(self):
        for i, _ in enumerate(self.segments, start=1):
            video = self.output_folder / f"{i}.mp4"
            audio = self.output_folder / f"{i}.mp3"
            out = self.output_folder / f"updated{i}.mp4"

            subprocess.run([
                "ffmpeg", "-y",
                "-i", str(video),
                "-i", str(audio),
                "-c:v", "copy",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(out)
            ], check=True)

            print(f"✅ Merged updated{i}.mp4")

            # Cleanup split files immediately
            video.unlink()
            audio.unlink()

    # -----------------------
    # Extract middle frame
    # -----------------------
    def extract_images(self):
        for i, _ in enumerate(self.segments, start=1):
            video = self.output_folder / f"updated{i}.mp4"
            image = self.output_folder / f"updated{i}image.jpg"

            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video)
            ], capture_output=True, text=True, check=True)

            duration = float(result.stdout.strip())
            pick_time = duration * 0.4

            subprocess.run([
                "ffmpeg", "-y",
                "-ss", f"{pick_time:.3f}",
                "-i", str(video),
                "-frames:v", "1",
                "-q:v", "2",
                str(image)
            ], check=True)

            print(f"🖼 Image extracted {image.name}")

    # -----------------------
    # Create sequential grid with black gap
    # -----------------------
    def create_sequential_grid(self):
        if len(self.segments) != 2:
            raise ValueError("Exactly 2 segments required")

        v1 = self.output_folder / "updated1.mp4"
        v2 = self.output_folder / "updated2.mp4"
        img1 = self.output_folder / "updated1image.jpg"
        img2 = self.output_folder / "updated2image.jpg"

        seg1 = self.output_folder / "seg1.mp4"
        seg2 = self.output_folder / "seg2.mp4"

        # Segment 1 (top video1, bottom image2)
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(v1),
            "-loop", "1", "-i", str(img2),
            "-filter_complex",
            f"[0:v]scale={self.mobile_width}:-2[top];"
            f"[1:v]scale={self.mobile_width}:-2[bot];"
            f"color=c=black:s={self.mobile_width}x{self.gap_height}[gap];"
            "[top][gap][bot]vstack=inputs=3",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-movflags", "+faststart",
            "-shortest",
            str(seg1)
        ], check=True)

        # Segment 2 (top image1, bottom video2)
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(img1),
            "-i", str(v2),
            "-filter_complex",
            f"[0:v]scale={self.mobile_width}:-2[top];"
            f"[1:v]scale={self.mobile_width}:-2[bot];"
            f"color=c=black:s={self.mobile_width}x{self.gap_height}[gap];"
            "[top][gap][bot]vstack=inputs=3",
            "-map", "1:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-movflags", "+faststart",
            "-shortest",
            str(seg2)
        ], check=True)

        # Concat
        concat_list = self.output_folder / "concat.txt"
        concat_list.write_text(f"file '{seg1.resolve()}'\nfile '{seg2.resolve()}'\n")

        final_out = self.output_folder / "final_grid_seq.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(final_out)
        ], check=True)

        print(f"✅ Final output → {final_out}")

        # Cleanup all intermediates
        files_to_cleanup = list(self.output_folder.glob("updated*.mp4")) + \
                           list(self.output_folder.glob("updated*image.*")) + \
                           [seg1, seg2, concat_list]

        for f in files_to_cleanup:
            if f.exists():
                f.unlink()

    # -----------------------
    # Run all
    # -----------------------
    def run_pipeline(self):
        self.split_video_audio()
        self.merge_clips()
        self.extract_images()
        self.create_sequential_grid()
        print("🎉 Pipeline complete!")


# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    pipeline = SequentialGridVideoPipeline(
        input_file="videos_processing/inputs/videos/5.mp4",
        segments=[(0, 5), (5, 10)],
        output_folder="videos_processing/outputs/5_segments_grid",
        mobile_width=720,
        gap_height=60  # 🔥 increase/decrease middle black bar
    )

    pipeline.run_pipeline()

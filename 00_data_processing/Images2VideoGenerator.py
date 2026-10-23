import os
from pathlib import Path
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_audioclips,
)

class Images2VideoGenerator:
    """
    A generic Object-Oriented utility class to compile sequential images into high-quality
    rendered informational videos featuring customized pan/zoom motion overlays.
    """
    def __init__(
        self,
        image_folder,
        audio_file=None,
        output_folder=None,
        video_width=1080,
        video_height=1920,
        video_duration=59,
        fps=30,
        zoom_percent=0.05
    ):
        self.image_folder = Path(image_folder)
        self.audio_file = audio_file
        
        # If output path isn't explicitly defined, replace "images" with "videos" in the directory tree
        if output_folder:
            self.output_folder = Path(output_folder)
        else:
            self.output_folder = Path(str(self.image_folder).replace("images", "videos"))
            
        self.video_width = video_width
        self.video_height = video_height
        self.video_duration = video_duration
        self.fps = fps
        self.zoom_percent = zoom_percent
        
        # Internal placeholders
        self.audio_clip = None

    def _load_audio_asset(self):
        """Loads and prepares background audio clip components safely."""
        if self.audio_file and os.path.exists(self.audio_file):
            print(f"Loading background audio: {self.audio_file}")
            self.audio_clip = AudioFileClip(str(self.audio_file))
        else:
            print("Warning: Audio target reference not found. Output videos will be silent.")
            self.audio_clip = None

    def _process_audio_duration(self):
        """Loops or subclips audio timeline tracks to fit the targeted video duration boundaries exactly."""
        if not self.audio_clip:
            return None
            
        if self.audio_clip.duration >= self.video_duration:
            return self.audio_clip.subclipped(0, self.video_duration)
        
        # Calculate repetitions needed to pad full runtime sequence safely
        loops_needed = int(self.video_duration / self.audio_clip.duration) + 1
        extended_audio = concatenate_audioclips([self.audio_clip] * loops_needed)
        return extended_audio.subclipped(0, self.video_duration)

    def generate_videos(self, overwrite=False):
        """Iterates over the discovered image folder assets and builds the final video files."""
        if not self.image_folder.exists():
            raise FileNotFoundError(f"Target distribution folder path missing: {self.image_folder}")

        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        image_files = sorted(
            f for f in self.image_folder.iterdir()
            if f.suffix.lower() == ".png"
        )
        
        print(f"Found {len(image_files)} source frames to convert inside target directory.")
        
        # Setup and cache base global sound profiles
        self._load_audio_asset()

        for image_path in image_files:
            output_video_path = self.output_folder / f"{image_path.stem}.mp4"

            if output_video_path.exists() and not overwrite:
                print(f"Skipping existing render: {image_path.name}")
                continue

            print(f"Compiling: {image_path.name} -> {output_video_path.name}")

            # Calculate precise scale vectors to balance framing margins smoothly
            temp_clip = ImageClip(str(image_path))
            base_scale = min(self.video_width / temp_clip.w, self.video_height / temp_clip.h)
            temp_clip.close()

            # Dynamic inner inline functional transformer hook for MoviePy zoom mechanics
            def zoom_transform(time_offset):
                return base_scale * (
                    1 + self.zoom_percent * (time_offset / self.video_duration)
                )

            # Build layout element instances
            foreground_layer = (
                ImageClip(str(image_path))
                .resized(zoom_transform)
                .with_duration(self.video_duration)
                .with_position("center")
            )

            composite_canvas = CompositeVideoClip(
                [foreground_layer],
                size=(self.video_width, self.video_height)
            ).with_duration(self.video_duration)

            # Assign audio tracks
            active_audio = self._process_audio_duration()
            if active_audio:
                composite_canvas = composite_canvas.with_audio(active_audio)

            # Render compilation block execution
            composite_canvas.write_videofile(
                str(output_video_path),
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                threads=min(4, os.cpu_count() or 1),
            )

            # Cleanup step instances per iteration
            composite_canvas.close()
            foreground_layer.close()

        # Release audio file resources when execution chain wraps
        if self.audio_clip:
            self.audio_clip.close()
            
        print(f"\nExecution complete! Process logs output vectors stored directly at:\n{self.output_folder}")
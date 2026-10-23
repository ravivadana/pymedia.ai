import os
import numpy as np
from PIL import Image
from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    concatenate_audioclips,
    VideoClip
)

class Image2VideoGenerator:
    """
    An OOP-based engine to process high-resolution infographic sheets
    and compile them into smooth, mobile-optimized static/stretched MP4 videos.
    """
    def __init__(self, target_width=1080, target_height=1920, default_duration=12, fps=30, audio=None):
        """
        Initializes the video rendering pipeline layout configurations.
        """
        self.target_w = target_width
        self.target_h = target_height
        self.default_duration = default_duration
        self.fps = fps
        self.bg_color = (12, 28, 54)  # Matches your DARK_BLUE configuration

        self.audio_track = None
        if os.path.exists(audio):
            print(f"OOP Engine: Loading audio track -> {os.path.basename(audio)}")
            self.audio_track = AudioFileClip(audio)
        else:
            print(f"WARNING: Audio file not found at '{audio}'. Video will render without sound.")
            self.audio = audio

    def _prepare_image(self, image_path):
        """
        Internal helper: Loads and forcibly stretches the source graphic 
        to perfectly match both target video width and height.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found at: {image_path}")
            
        pil_img = Image.open(image_path).convert("RGB")
        
        # Forcibly stretch image to match both target width and height dimensions
        resized_img = pil_img.resize((self.target_w, self.target_h), Image.Resampling.LANCZOS)
        
        return resized_img

    def generate_scrolling_video(self, image_path, output_mp4_path, duration=None):
        """
        Compiles a data matrix image stretched into a vertical static mobile MP4 video clip.
        """
        # Fall back to default constructor duration if none is passed dynamically
        self.default_duration = duration if duration is not None else self.default_duration
        
        try:
            resized_img = self._prepare_image(image_path)
        except FileNotFoundError as e:
            print(f"CRITICAL ERROR: {e}")
            return

        # Pre-convert the full stretched PIL image directly to a NumPy array once
        # to maximize frame generation performance efficiency.
        frame_array = np.array(resized_img)

        def frame_generator(t):
            """Returns the pre-rendered stretched array frame over timestamp 't'"""
            return frame_array

        print(f"OOP Engine: Processing stretched layout video for -> {os.path.basename(image_path)}")
        
        # Normalize path separators to match your operating system (Windows vs Mac/Linux)
        clean_output_path = os.path.normpath(output_mp4_path)

        # =====================================================
        # SKIP CHECK
        # =====================================================
        if os.path.exists(clean_output_path):
            print(f"SKIP: '{os.path.basename(clean_output_path)}' already exists. Skipping generation...")
            return  # Exits the method early and continues the script
            
        # Extract the directory portion and create it if it doesn't exist yet
        output_dir = os.path.dirname(clean_output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Build MoviePy Video Clip runtime sequence
        clip = VideoClip(frame_generator, duration=self.default_duration)

        # =====================================================
        # COMPOSITE VIDEO
        # =====================================================
        video = CompositeVideoClip(
            [clip],
            size=(self.target_w, self.target_h)
        ).with_duration(self.default_duration)

        # =====================================================
        # AUDIO
        # =====================================================
        if self.audio_track is not None:
            if self.audio_track.duration >= self.default_duration:
                clip_audio = self.audio_track.subclipped(0, self.default_duration)
            else:
                loops = int(self.default_duration / self.audio_track.duration) + 1
                clip_audio = concatenate_audioclips([self.audio_track] * loops).subclipped(
                    0,
                    self.default_duration
                )
            # Apply audio only if self.audio was present
            video = video.with_audio(clip_audio)

        # =====================================================
        # EXPORT
        # =====================================================
        video.write_videofile(
            str(clean_output_path),
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=min(4, os.cpu_count() or 1) # Guard against cpu_count returning None
        )        
        
        # Clean system memory allocation
        clip.close()
        video.close() # Good practice to close the composite video object as well
        print(f"SUCCESS: Video file successfully exported to -> {clean_output_path}\n")


# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    # 1. Instantiate the generator class object configuration
    video_engine = Image2VideoGenerator(
        target_width=1080, 
        target_height=1920, 
        default_duration=12, 
        fps=30
    )
    
    # 2. Map input configurations
    input_chart = "00_data_processing/images/nrif_ranking/2026/engineering/category_matrix/00_OPEN_Category_Matrix.png"
    output_video = "00_data_processing/videos/nrif_ranking/2026/engineering/category_matrix/OPEN_Category_Matrix.mp4"
    
    # 3. Trigger compilation process using instance methods
    video_engine.generate_scrolling_video(input_chart, output_video)
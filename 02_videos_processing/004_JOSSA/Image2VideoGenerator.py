import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    concatenate_audioclips,
    VideoClip
)

class Image2VideoGenerator:
    """
    An OOP-based engine to process high-resolution infographic sheets
    and compile them into smooth, mobile-optimized static or slideshow MP4 videos.
    """
    def __init__(self, target_width=1080, target_height=1920, default_duration=12, fps=30, audio=None):
        """
        Initializes the video rendering pipeline layout configurations.
        """
        self.target_w = target_width
        self.target_h = target_height
        self.default_duration = default_duration
        self.fps = fps
        
        # Color palette extracted from the stylized image
        self.color_dark = (11, 23, 44)
        self.color_light = (23, 55, 99)

        self.audio_track = None
        if audio and os.path.exists(audio):
            print(f"OOP Engine: Loading audio track -> {os.path.basename(audio)}")
            self.audio_track = AudioFileClip(audio)
        elif audio:
            print(f"WARNING: Audio file not found at '{audio}'. Video will render without sound.")

    def _create_gradient_background(self):
        """
        Generates a premium background using diagonal gradients, smooth layered vector arcs,
        and Gaussian blur drop shadows to emulate a professional UI environment.
        """
        # 1. Generate the base linear diagonal gradient
        base = Image.new("RGB", (self.target_w, self.target_h), self.color_dark)
        top_layer = Image.new("RGB", (self.target_w, self.target_h), self.color_light)
        
        mask = Image.new("L", (self.target_w, self.target_h))
        for y in range(self.target_h):
            for x in range(self.target_w):
                # Diagonal calculation normalized between 0 and 255
                factor = (x / self.target_w + y / self.target_h) / 2.0
                mask.putpixel((x, y), int(factor * 255))
                
        canvas = Image.composite(top_layer, base, mask)
        
        # 2. Draw organic shadow/light shapes (Upper-right curve & Lower-left curve)
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Top-right decorative background fold
        draw.chord(
            [self.target_w // 3, -self.target_h // 6, self.target_w * 1.5, self.target_h // 3],
            start=0, end=360, fill=(35, 74, 128, 40)
        )
        
        # Bottom-left decorative background fold
        draw.chord(
            [-self.target_w // 2, self.target_h // 1.3, self.target_w // 1.2, self.target_h * 1.2],
            start=0, end=360, fill=(15, 34, 64, 130)
        )
        
        # Smooth out vector lines to blend shapes naturally into shadows
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=40))
        canvas.paste(overlay, (0, 0), overlay)
        
        return canvas.convert("RGB")

    def _prepare_image(self, image_path):
        """
        Internal helper: Loads and resizes a source graphic proportionally to fit 
        the target width, then centers it over the dynamic gradient backdrop.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found at: {image_path}")
            
        pil_img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = pil_img.size
        
        # 1. Calculate aspect ratio scaling based on target width
        aspect_ratio = orig_h / orig_w
        new_w = self.target_w
        new_h = int(new_w * aspect_ratio)
        
        # Resize image proportionally to prevent stretching text/fonts
        resized_aspect_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 2. Compile background generation instead of flat color
        canvas = self._create_gradient_background()
        
        # 3. Position and center the image vertically
        if new_h <= self.target_h:
            paste_y = (self.target_h - new_h) // 2
            canvas.paste(resized_aspect_img, (0, paste_y))
        else:
            crop_y = (new_h - self.target_h) // 2
            canvas.paste(resized_aspect_img.crop((0, crop_y, self.target_w, crop_y + self.target_h)), (0, 0))
        
        return canvas

    def generate_video(self, image_path, output_mp4_path, duration=None):
        """
        Compiles either a single data matrix image or a list of sequence images 
        into a vertical mobile MP4 video clip.
        """
        self.default_duration = duration if duration is not None else self.default_duration
        clean_output_path = os.path.normpath(output_mp4_path)

        # =====================================================
        # SKIP CHECK
        # =====================================================
        if os.path.exists(clean_output_path):
            print(f"SKIP: '{os.path.basename(clean_output_path)}' already exists. Skipping generation...")
            return
            
        output_dir = os.path.dirname(clean_output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # =====================================================
        # CORE FRAME GENERATION (Handles Strings or Lists)
        # =====================================================
        if isinstance(image_path, list):
            print(f"OOP Engine: Preparing sequence slideshow of {len(image_path)} images...")
            
            # Pre-render every image in the list to NumPy arrays
            frame_arrays = []
            for path in image_path:
                try:
                    resized_img = self._prepare_image(path)
                    frame_arrays.append(np.array(resized_img))
                except FileNotFoundError as e:
                    print(f"WARNING: Skipping frame due to missing asset: {e}")
            
            if not frame_arrays:
                print("CRITICAL ERROR: No valid images found to compile sequence video.")
                return

            def frame_generator(t):
                """Calculates current time slide index seamlessly across total duration"""
                idx = int((t / self.default_duration) * len(frame_arrays))
                if idx >= len(frame_arrays):
                    idx = len(frame_arrays) - 1
                return frame_arrays[idx]

        else:
            # Single Image String Mode Flow
            try:
                resized_img = self._prepare_image(image_path)
            except FileNotFoundError as e:
                print(f"CRITICAL ERROR: {e}")
                return

            frame_array = np.array(resized_img)

            def frame_generator(t):
                return frame_array

            print(f"OOP Engine: Processing centered layout video for -> {os.path.basename(image_path)}")

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
        # AUDIO TRACKING
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
            video = video.with_audio(clip_audio)

        # =====================================================
        # EXPORT PIPELINE
        # =====================================================
        video.write_videofile(
            str(clean_output_path),
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=min(4, os.cpu_count() or 1)
        )        
        
        clip.close()
        video.close()
        print(f"SUCCESS: Video file successfully exported to -> {clean_output_path}\n")
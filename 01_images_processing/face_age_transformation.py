# age_morph_with_bg_audio.py

import cv2
import numpy as np
import imageio
import os
from PIL import Image
from moviepy import VideoFileClip

try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False


class AgeMorpher:
    def __init__(self, image_paths, output_video="age_progression_final.mp4",
                 video_size=(512, 512), fps=24, frames_per_transition=150,
                 background_video_path=None):
        """
        image_paths: list of images [child, young, middle age, old]
        background_video_path: optional path to background video (for visuals + audio)
        """
        self.image_paths = image_paths
        self.output_video = output_video
        self.video_size = video_size
        self.fps = fps
        self.frames_per_transition = frames_per_transition
        self.background_video_path = background_video_path
        self.use_bg = background_video_path is not None
        self.images = self._load_images()

        if self.use_bg:
            self.bg_frames = self._load_background_frames()
            if not REMBG_AVAILABLE:
                raise ImportError("rembg is required for background video. Install with `pip install rembg`.")

    def _load_images(self):
        imgs = []
        for path in self.image_paths:
            img = cv2.imread(path)
            if img is None:
                raise ValueError(f"Image not found: {path}")
            img = cv2.resize(img, self.video_size)

            # If background video is used, remove background
            if self.use_bg:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(img_rgb)
                img_no_bg = remove(pil_img).convert("RGB")
                img_no_bg = img_no_bg.resize(self.video_size)
                img = cv2.cvtColor(np.array(img_no_bg), cv2.COLOR_RGB2BGR)

            imgs.append(img)
        return imgs

    def _load_background_frames(self):
        cap = cv2.VideoCapture(self.background_video_path)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_resized = cv2.resize(frame, self.video_size)
            frames.append(frame_resized)
        cap.release()
        if len(frames) == 0:
            raise ValueError("Background video could not be loaded")
        return frames

    def _morph_images(self, img1, img2):
        frames = []
        for alpha in np.linspace(0, 1, self.frames_per_transition):
            frame = cv2.addWeighted(img1, 1 - alpha, img2, alpha, 0)
            frames.append(frame)
        return frames

    def create_video(self):
        print("Creating age progression video...")
        all_morph_frames = []

        # Generate morph frames
        for i in range(len(self.images) - 1):
            morph_frames = self._morph_images(self.images[i], self.images[i+1])
            all_morph_frames.extend(morph_frames)

        # Write temporary video without audio
        temp_video = self.output_video.replace(".mp4", "_temp.mp4")
        os.makedirs(os.path.dirname(temp_video), exist_ok=True)
        writer = imageio.get_writer(temp_video, fps=self.fps)

        if self.use_bg:
            bg_len = len(self.bg_frames)
            for idx, face_frame in enumerate(all_morph_frames):
                bg_frame = self.bg_frames[idx % bg_len]  # loop background
                combined = bg_frame.copy()
                mask = np.any(face_frame != 0, axis=2)
                combined[mask] = face_frame[mask]
                writer.append_data(combined)
        else:
            for frame in all_morph_frames:
                writer.append_data(frame)

        writer.close()
        print(f"✅ Temporary video saved: {temp_video}")

        # Apply audio from background video if provided
        if self.use_bg:
            print("Applying audio from background video...")
            bg_clip = VideoFileClip(self.background_video_path)
            morph_clip = VideoFileClip(temp_video)
            # Use the background video audio
            morph_clip = morph_clip.set_audio(bg_clip.audio.set_duration(morph_clip.duration))
            morph_clip.write_videofile(self.output_video, fps=self.fps)
            print(f"✅ Final video saved with background audio: {self.output_video}")
        else:
            # No background video, just rename temp video
            os.rename(temp_video, self.output_video)
            print(f"✅ Final video saved without audio: {self.output_video}")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    image_list = [
        "images_processing/images/child.png",
        "images_processing/images/middle_age.jpg",
        "images_processing/images/old.jpg"
    ]

    background_video = "images_processing/videos/background.mp4"  # use your mp4 with audio, or None

    morpher = AgeMorpher(
        image_paths=image_list,
        output_video="images_processing/videos/age_progression_with_bg_audio.mp4",
        video_size=(512, 512),
        fps=24,
        frames_per_transition=150,
        background_video_path=None  # set to None if no audio/video
    )
    morpher.create_video()

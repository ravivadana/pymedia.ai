import json
import os
import random
import textwrap
import shutil
import unicodedata
import re
import subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips
import sys

class PremiumVideoEngine:
    """Takes pre-rendered frames from the disk, applies custom audio loops via ffmpeg, 
    and outputs smooth, scrolling mp4 tracks.
    """

    def __init__(self, config):
        self.config = config
        os.makedirs(os.path.dirname(self.config["output_video_path"]), exist_ok=True)

    def create_video(self):
        # Quick bypass if the video target already exists
        if os.path.exists(self.config["output_video_path"]):
            return self.config["output_video_path"]
            
        intro_img_path = os.path.join(self.config["mobile_folder"], "000_intro.png")
        end_img_path = os.path.join(self.config["mobile_folder"], "999_end.png")

        if not os.path.exists(intro_img_path) or not os.path.exists(end_img_path):
            print("X Compile error: Static structures missing from source path workspace.")
            return

        mobile_images = sorted(
            [
                os.path.join(self.config["mobile_folder"], f)
                for f in os.listdir(self.config["mobile_folder"])
                if f.endswith(".png")
                and not (f.startswith("000_") or f.startswith("999_"))
            ]
        )

        if not mobile_images:
            print("X Compile error: No scrolling layout parts discovered.")
            return

        print("\nCompiling Video Track via Stream-Optimized Scroll Engine...")
        total_scroll_height = 0
        canvas_positions = []

        for p in mobile_images:
            with Image.open(p) as img_obj:
                canvas_positions.append(total_scroll_height)
                total_scroll_height += img_obj.height

        long_canvas = Image.new(
            "RGB",
            (self.config["mobile_width"], total_scroll_height),
            (252, 252, 253),
        )
        for idx, p in enumerate(mobile_images):
            with Image.open(p) as img_obj:
                long_canvas.paste(
                    img_obj.convert("RGB"), (0, canvas_positions[idx])
                )

        last_list_viewport = long_canvas.crop(
            (
                0,
                total_scroll_height - self.config["mobile_height"],
                self.config["mobile_width"],
                total_scroll_height,
            )
        )
        last_list_np = np.array(last_list_viewport)

        total_scroll_pixels = total_scroll_height - self.config["mobile_height"]
        scroll_duration = total_scroll_pixels / (
            self.config["scroll_speed"] * self.config["fps"]
        )

        intro_clip = ImageClip(intro_img_path).with_duration(3.5)
        end_clip = ImageClip(end_img_path).with_duration(4.0)

        def scroll_frame_processor(get_frame, t):
            current_y = int(t * self.config["fps"] * self.config["scroll_speed"])
            current_y = min(current_y, total_scroll_pixels)
            viewport = long_canvas.crop(
                (
                    0,
                    current_y,
                    self.config["mobile_width"],
                    current_y + self.config["mobile_height"],
                )
            )
            return np.array(viewport)

        scroll_base = ImageClip(last_list_np).with_duration(scroll_duration)
        scroll_clip = scroll_base.transform(scroll_frame_processor, apply_to=[])

        fade_duration = 0.8
        end_np = np.array(Image.open(end_img_path).convert("RGB"))

        def fade_frame_processor(get_frame, t):
            alpha = min(max(t / fade_duration, 0.0), 1.0)
            blended = np.clip(
                (last_list_np * (1.0 - alpha) + end_np * alpha), 0, 255
            ).astype(np.uint8)
            return blended

        fade_base = ImageClip(last_list_np).with_duration(fade_duration)
        fade_clip = fade_base.transform(fade_frame_processor, apply_to=[])

        # Stitch visual components together
        main_video = concatenate_videoclips(
            [intro_clip, scroll_clip, fade_clip, end_clip], method="chain"
        )
        
        video_duration = main_video.duration

        # Path for a temporary silent video file
        temp_silent_video = os.path.join(os.path.dirname(self.config["output_video_path"]), "temp_silent_track.mp4")

        print(f"Rendering silent base video: {temp_silent_video}...")
        main_video.write_videofile(
            temp_silent_video,
            fps=self.config["fps"],
            codec="libx264",
            audio=False, # Output purely silent track to prevent internal errors
            preset="medium",
            threads=4,
            logger="bar",
        )

        # Clean closures across active MoviePy streams early to release file locks
        main_video.close()
        intro_clip.close()
        scroll_clip.close()
        fade_clip.close()
        end_clip.close()
        long_canvas.close()
        last_list_viewport.close()
       
        # --- NATIVE FFMPEG AUDIO INJECTION & LOOP PIPELINE ---
        if "audio_path" in self.config and os.path.exists(self.config["audio_path"]):
            print(f"Injecting audio layout soundtrack via FFmpeg: {self.config['audio_path']}...")
            try:
                out_path = self.config["output_video_path"]
                fade_start = max(0.0, video_duration - 2.0)
                
                # Fetch volume modifier from configuration (defaulting to 15% if missing)
                volume_level = self.config.get("bgm_volume", 0.15)
                
                # FFmpeg compound complex filter description:
                # 1. Selects the audio stream from our input BGM asset ([1:a])
                # 2. Applies a volume reduction constraint to it ('volume=X')
                # 3. Chains it smoothly into the clean 2-second linear fade-out stream filter ('afade')
                audio_filter_chain = f"[1:a]volume={volume_level},afade=t=out:st={fade_start}:d=2.0[a]"
                
                cmd = [
                    'ffmpeg', '-y',
                    '-i', temp_silent_video,
                    '-stream_loop', '-1', '-i', self.config["audio_path"],
                    '-filter_complex', audio_filter_chain,
                    '-map', '0:v',
                    '-map', '[a]',
                    '-c:v', 'copy', # Copy video stream without re-encoding (instant stream execution)
                    '-c:a', 'aac',
                    '-shortest', # Drop extra looped audio when the video length finishes
                    out_path
                ]
                
                # Run the subprocess hiddenly
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                print(f"FFmpeg pipeline processed audio loop successfully.")
                
                # Clean up temporary silent render
                if os.path.exists(temp_silent_video):
                    os.remove(temp_silent_video)
                    
            except Exception as ffmpeg_err:
                print(f"X Warning: FFmpeg layout assembly error: {ffmpeg_err}")
                # Fallback safety switch: use the silent video as output instead of completely breaking
                if os.path.exists(temp_silent_video):
                    shutil.move(temp_silent_video, self.config["output_video_path"])
        else:
            print("! No background audio path found. Finalizing silent track output.")
            if os.path.exists(temp_silent_video):
                shutil.move(temp_silent_video, self.config["output_video_path"])
            
        self.cleanup_workspace()
        return self.config["output_video_path"]

    def cleanup_workspace(self):
        print("\nCleaning temporary folders...")
        for folder in [self.config["temp_folder"], self.config["mobile_folder"]]:
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
                print(f"Deleted: {folder}")
        print("\nPipeline Complete!")
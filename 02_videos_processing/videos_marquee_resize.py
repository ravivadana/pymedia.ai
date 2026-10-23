import cv2
import numpy as np
import os
import subprocess
from pathlib import Path
from collections import Counter
from PIL import Image, ImageFont, ImageDraw, ImageFilter


class VideosMarqueeResize:

    # ---------- Optimal resize (aspect-safe, no bars) ----------
    def resize_center_crop(self, frame, target_w, target_h):
        h, w = frame.shape[:2]

        scale = max(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        x1 = (new_w - target_w) // 2
        y1 = (new_h - target_h) // 2

        return resized[y1:y1 + target_h, x1:x1 + target_w]

    # ---------- Marquee shifting ----------
    def apply_marquee_shift(self, stacked, offset, direction, w, h):
        if direction == "up":
            M = np.float32([[1, 0, 0], [0, 1, -offset]])
        elif direction == "down":
            M = np.float32([[1, 0, 0], [0, 1, offset]])
        elif direction == "left":
            M = np.float32([[1, 0, -offset], [0, 1, 0]])
        elif direction == "right":
            M = np.float32([[1, 0, offset], [0, 1, 0]])
        elif direction == "diagonal":
            M = np.float32([[1, 0, offset], [0, 1, offset]])
        else:
            raise ValueError("Invalid direction")

        shifted = cv2.warpAffine(
            stacked,
            M,
            (stacked.shape[1], stacked.shape[0]),
            borderMode=cv2.BORDER_WRAP
        )

        return shifted[:h, :w]

    def add_caption(
        self, 
        frame, 
        text_block, 
        current_frame_idx,
        fps,
        font_size=42, 
        text_color=(255, 0, 0),       # Changed to Red font color (RGB)
        outline_color=(0, 0, 0),  
        font_path="arial.ttf", 
        max_width_ratio=0.88
    ):
        """
        Renders multi-line text positioned low down inside a yellow background box container 
        featuring a crisp border and red font.
        """
        if not text_block:
            return frame

        frame_h, frame_w = frame.shape[:2]
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # Try loading the user-provided font, with fallback options if unavailable
        font = None
        fonts_to_try = [font_path, "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
        for f_name in fonts_to_try:
            try:
                font = ImageFont.truetype(f_name, font_size)
                break
            except IOError:
                continue
                
        if font is None:
            font = ImageFont.load_default()
            print("Warning: Specified or standard TTF fonts not found. Falling back to default font.")

        normalized_text = text_block.replace('\\n', '\n')
        raw_lines = [line.strip() for line in normalized_text.split('\n') if line.strip()]
        
        max_allowed_width = int(frame_w * max_width_ratio)
        wrapped_lines = []
        
        for raw_line in raw_lines:
            words = raw_line.split(" ")
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                bbox = font.getbbox(test_line)
                w = bbox[2] - bbox[0]
                if w <= max_allowed_width:
                    current_line = test_line
                else:
                    if current_line:
                        wrapped_lines.append(current_line)
                    current_line = word
            if current_line:
                wrapped_lines.append(current_line)

        if not wrapped_lines:
            return frame

        line_heights = []
        line_widths = []
        for line in wrapped_lines:
            bbox = font.getbbox(line)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append((bbox[3] - bbox[1]) + 10)

        total_text_h = sum(line_heights)
        max_text_w = max(line_widths) if line_widths else 0

        start_x = (frame_w - max_text_w) // 2
        start_y = ((frame_h - total_text_h) // 2) + 460

        padding_x = 45
        padding_y = 30
        box_x1 = start_x - padding_x
        box_y1 = start_y - padding_y
        box_x2 = start_x + max_text_w + padding_x
        box_y2 = start_y + total_text_h + padding_y

        # 1. Create Drop Shadow Layer
        shadow_offset_x = 4
        shadow_offset_y = 6
        shadow_layer = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        shadow_draw.rounded_rectangle(
            [box_x1 + shadow_offset_x, box_y1 + shadow_offset_y, box_x2 + shadow_offset_x, box_y2 + shadow_offset_y],
            radius=25,
            fill=(0, 0, 0, 120)  # Semi-transparent black shadow
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(6))

        # 2. Create Yellow Box Layer with a Clean Border
        box_layer = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
        box_draw = ImageDraw.Draw(box_layer)
        
        # Draw rounded rectangle with Yellow background (e.g., alpha 220 for slight transparency, or use 255 for solid yellow)
        box_draw.rounded_rectangle(
            [box_x1, box_y1, box_x2, box_y2],
            radius=25,
            fill=(255, 255, 0, 220),    # Yellow background with transparency
            outline=(0, 0, 0, 255),       # Dark/Black border for contrast against yellow
            width=2                       # Border thickness
        )

        # 3. Draw Text onto Text Overlay Layer
        txt_overlay = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_overlay)

        current_y = start_y

        for i, line in enumerate(wrapped_lines):
            line_w = line_widths[i]
            line_x = start_x + (max_text_w - line_w) // 2

            # Optional: Add a subtle white outline/glow around the red text to make it pop even more on yellow background
            outline_width = 2
            for ox in range(-outline_width, outline_width + 1):
                for oy in range(-outline_width, outline_width + 1):
                    if ox != 0 or oy != 0:
                        txt_draw.text((line_x + ox, current_y + oy), line, font=font, fill=(255, 255, 255, 255))

            # Draw Red Text
            txt_draw.text((line_x, current_y), line, font=font, fill=text_color + (255,))
            current_y += line_heights[i]

        # Combine all layers: Base image -> Shadow -> Yellow Box -> Text Overlay
        combined = Image.alpha_composite(img_pil.convert("RGBA"), shadow_layer)
        combined = Image.alpha_composite(combined, box_layer)
        combined = Image.alpha_composite(combined, txt_overlay)

        return cv2.cvtColor(np.array(combined.convert("RGB")), cv2.COLOR_RGB2BGR)

    # ---------- Main ----------
    def create_marquee_video(self, input_dir, output_dir, direction, caption_block=None, font_path="arial.ttf"):
        extensions = (".mp4", ".mov", ".avi", ".webm")
        os.makedirs(output_dir, exist_ok=True)

        video_files = [
            os.path.join(input_dir, f)
            for f in os.listdir(input_dir)
            if f.lower().endswith(extensions)
        ]

        if len(video_files) < 2:
            raise RuntimeError("Need at least 2 videos")

        durations = []
        for vf in video_files:
            cap = cv2.VideoCapture(vf)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            durations.append((vf, frames / fps))
            cap.release()

        video_files = [v for v, _ in sorted(durations, key=lambda x: x[1], reverse=True)]

        size_counter = Counter()
        for vf in video_files:
            cap = cv2.VideoCapture(vf)
            ret, frame = cap.read()
            cap.release()
            if ret:
                h, w = frame.shape[:2]
                size_counter[(w, h)] += 1

        if not size_counter:
            raise RuntimeError("No readable video frames")

        ref_w, ref_h = size_counter.most_common(1)[0][0]
        print(f"Reference size: {ref_w}x{ref_h}")

        first_video = video_files[0]
        cap = cv2.VideoCapture(first_video)
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = frame_count / fps
        cap.release()

        fade_height = max(10, ref_h // 10)

        caps = [cv2.VideoCapture(v) for v in video_files]

        temp_video = f"{output_dir}/temp_{Path(first_video).name}"
        final_video = f"{output_dir}/final_{Path(first_video).name}"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(temp_video, fourcc, fps, (ref_w, ref_h))

        def cross_fade(a, b, fh):
            alpha = np.linspace(0, 1, fh)[:, None, None]
            return ((1 - alpha) * a[-fh:] + alpha * b[:fh]).astype(np.uint8)

        frame_buffer = []
        for cap in caps:
            ret, f = cap.read()
            if not ret:
                raise RuntimeError("Frame read error")
            f = self.resize_center_crop(f, ref_w, ref_h)
            frame_buffer.append(f)

        strip_height = len(frame_buffer) * (ref_h - fade_height) + fade_height * (len(frame_buffer) - 1)
        total_frames = int(fps * duration_sec)
        speed = strip_height / total_frames
        offset = 0.0

        for frame_idx in range(total_frames):
            tall_strip = []

            for i in range(len(frame_buffer) - 1):
                A = frame_buffer[i]
                B = frame_buffer[i + 1]
                tall_strip.append(A[:-fade_height])
                tall_strip.append(cross_fade(A, B, fade_height))

            tall_strip.append(frame_buffer[-1][:-fade_height])
            stacked = np.vstack(tall_strip)

            out_frame = self.apply_marquee_shift(stacked, offset, direction, ref_w, ref_h)
            
            if caption_block:
                out_frame = self.add_caption(out_frame, caption_block, frame_idx, fps, font_path=font_path)

            out.write(out_frame)

            offset = (offset + speed) % stacked.shape[0]

            for i, cap in enumerate(caps):
                ret, f = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, f = cap.read()
                f = self.resize_center_crop(f, ref_w, ref_h)
                frame_buffer[i] = f

        out.release()
        for cap in caps:
            cap.release()

        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", first_video,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            final_video
        ], check=True)

        os.remove(temp_video)
        return final_video
import os
import platform
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, ImageClip as MoviePyImageClip, vfx, TextClip

class VideoGenerator:
    def __init__(self):
        self.canvas_w = 1080
        self.canvas_h = 1920
        self.flag_box_size = (480, 320)
        self.map_display_width = 750

    @staticmethod
    def create_soft_shape_mask(size, shape='circle', feather_pixels=30, corner_radius=8):
        w, h = size
        mask_img = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask_img)
        
        if shape == 'circle':
            radius = min(w, h) // 2
            center_x, center_y = w // 2, h // 2
            draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius], fill=255)
            if feather_pixels > 0:
                mask_img = mask_img.filter(ImageFilter.GaussianBlur(feather_pixels / 2))
        elif shape == 'rectangle':
            draw.rounded_rectangle([0, 0, w, h], radius=corner_radius, fill=255)
            if feather_pixels > 0:
                stretch_factor = 2.5  
                low_res_w = max(1, int(w / stretch_factor))
                mask_img = mask_img.resize((low_res_w, h), Image.Resampling.BILINEAR)
                mask_img = mask_img.filter(ImageFilter.GaussianBlur(feather_pixels / 2))
                mask_img = mask_img.resize((w, h), Image.Resampling.BILINEAR)
        elif shape == 'diamond':
            points = [(w // 2, 0), (w, h // 2), (w // 2, h), (0, h // 2)]
            draw.polygon(points, fill=255)
            if feather_pixels > 0:
                mask_img = mask_img.filter(ImageFilter.GaussianBlur(feather_pixels / 2))
        elif shape == 'star':
            center_x, center_y = w // 2, h // 2
            r_outer = min(w, h) // 2
            r_inner = r_outer // 2
            points = []
            for i in range(10):
                r = r_outer if i % 2 == 0 else r_inner
                angle = i * np.pi / 5 - np.pi / 2
                points.append((center_x + int(r * np.cos(angle)), center_y + int(r * np.sin(angle))))
            draw.polygon(points, fill=255)
            if feather_pixels > 0:
                mask_img = mask_img.filter(ImageFilter.GaussianBlur(feather_pixels / 2))
        else:
            draw.rectangle([0, 0, w, h], fill=255)
            if feather_pixels > 0:
                mask_img = mask_img.filter(ImageFilter.GaussianBlur(feather_pixels / 2))

        mask_array = np.array(mask_img).astype(float) / 255.0
        return ImageClip(mask_array, is_mask=True)

    @staticmethod
    def create_gradient_background(width, height, duration):
        top_color = np.random.randint(0, 256, size=3) 
        bottom_color = np.array([255, 255, 255])
        linear_mix = np.linspace(0, 1, height)[:, None, None]
        gradient_matrix = (1 - linear_mix) * top_color + linear_mix * bottom_color
        full_frame = np.tile(gradient_matrix.astype(np.uint8), (1, width, 1))
        return MoviePyImageClip(full_frame).with_duration(duration)

    def resolve_system_font(self):
        sys_plat = platform.system()
        possible_paths = []
        if sys_plat == "Windows":
            possible_paths = ["C:\\Windows\\Fonts\\ariblk.ttf", "C:\\Windows\\Fonts\\impact.ttf", "C:\\Windows\\Fonts\\arial.ttf"]
        elif sys_plat == "Darwin":
            possible_paths = ["/Library/Fonts/Arial Black.ttf", "/Library/Fonts/Impact.ttf", "/Library/Fonts/Arial.ttf"]
        else:
            possible_paths = ["/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return "Arial"

    def draw_geography_elements(self, pil_img, markers=None, target_coords=None):
        """
        Draws KIS-style interactive map elements directly on the background PIL Image.
        - markers: list of dicts with coordinate keys and values, e.g., [{'x': 500, 'y': 300, 'text': '86°F', 'color': '#D4AF37'}]
        - target_coords: tuple of (x, y) representing target/highlight region to draw crosshair & target border
        """
        draw = ImageDraw.Draw(pil_img)
        font_path = self.resolve_system_font()
        
        # Load a default small font for badges
        try:
            badge_font = ImageFont.truetype(font_path, 24)
        except Exception:
            badge_font = ImageFont.load_default()

        # 1. Draw temperature markers/badges
        if markers:
            for marker in markers:
                x, y = marker['x'], marker['y']
                text = marker['text']
                bg_color = marker.get('color', '#FFBF00') # Default golden orange
                text_color = marker.get('text_color', '#000000')

                # Calculate text size using drawing bounding box
                bbox = draw.textbbox((0, 0), text, font=badge_font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                
                # Draw rounded rectangle badge
                padding_x, padding_y = 12, 6
                badge_w = tw + (padding_x * 2)
                badge_h = th + (padding_y * 2)
                
                badge_x0 = x - badge_w // 2
                badge_y0 = y - badge_h // 2
                badge_x1 = badge_x0 + badge_w
                badge_y1 = badge_y0 + badge_h
                
                draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1], radius=6, fill=bg_color)
                # Draw text centered inside the badge
                draw.text((badge_x0 + padding_x, badge_y0 + padding_y - 2), text, font=badge_font, fill=text_color)

        # 2. Draw styled target crosshairs
        if target_coords:
            cx, cy = target_coords
            line_len = 25
            gap = 8
            crosshair_color = '#C71585' # Medium Violet Red/Pink outline theme
            
            # Draw crosshair tick lines (Top, Bottom, Left, Right)
            draw.line([(cx, cy - gap - line_len), (cx, cy - gap)], fill=crosshair_color, width=4)
            draw.line([(cx, cy + gap), (cx, cy + gap + line_len)], fill=crosshair_color, width=4)
            draw.line([(cx - gap - line_len, cy), (cx - gap, cy)], fill=crosshair_color, width=4)
            draw.line([(cx + gap, cy), (cx + gap + line_len, cy)], fill=crosshair_color, width=4)
            
            # Central target ring
            draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=crosshair_color)

        return pil_img

    def create_composite_video(self, sequence_str, main_video_path, center_png_path, bottom_gif_path, country_name, output_path, bg_image_path=None, shape='circle', force_replace=False, markers=None, target_coords=None):
        if os.path.exists(output_path) and not force_replace:
            return
            
        if os.path.exists(output_path) and force_replace:
            try: os.remove(output_path)
            except Exception: pass
            
        if shape == 'rectangle':
            box_w, box_h = self.canvas_w, 1100  
            main_clip_y, center_clip_y = 0, 720      
        else:
            box_w, box_h = 1050, 1050  
            main_clip_y, center_clip_y = 0, 700
            
        static_mask = self.create_soft_shape_mask((box_w, box_h), shape=shape, feather_pixels=30)
        
        try:
            main_clip_raw = VideoFileClip(main_video_path)
            duration = main_clip_raw.duration
            fps = min(main_clip_raw.fps, 30)
            vid_w, vid_h = main_clip_raw.size
            
            if shape == 'rectangle':
                target_ratio = box_w / box_h
                crop_w, crop_h = (int(vid_h * target_ratio), vid_h) if (vid_w / vid_h > target_ratio) else (vid_w, int(vid_w / target_ratio))
            else:
                crop_w = crop_h = min(vid_w, vid_h)
                
            # PERFORMANCE FIX & STYLE ENHANCEMENT: Pre-draw map overlays directly onto the map background image
            if bg_image_path and os.path.exists(bg_image_path):
                pil_bg = Image.open(bg_image_path).resize((self.canvas_w, self.canvas_h), Image.Resampling.BILINEAR)
                # Apply the satellite map styling overlays directly to the PIL image
                pil_bg = self.draw_geography_elements(pil_bg, markers=markers, target_coords=target_coords)
                bg_clip = ImageClip(np.array(pil_bg)).with_duration(duration)
            else:
                bg_clip = self.create_gradient_background(self.canvas_w, self.canvas_h, duration)
                
            cropped_clip = main_clip_raw.with_effects([vfx.Crop(x_center=vid_w // 2, y_center=vid_h // 2, width=crop_w, height=crop_h)])
            main_clip = (cropped_clip.resized(width=box_w, height=box_h)
                         .with_mask(static_mask.with_duration(duration))
                         .with_position(('center', main_clip_y)))
                         
            # Pre-size center map with PIL
            pil_map = Image.open(center_png_path)
            aspect_ratio = pil_map.height / pil_map.width
            target_map_h = int(self.map_display_width * aspect_ratio)
            pil_map_resized = pil_map.resize((self.map_display_width, target_map_h), Image.Resampling.BILINEAR)
            
            center_clip = (ImageClip(np.array(pil_map_resized)).with_duration(duration)
                           .with_position(('center', center_clip_y)))
                           
            font_resolved = self.resolve_system_font()
            text_str = f'{sequence_str}.{country_name.upper()}'
            box_size = (self.canvas_w, 200)
            
            base_font_size = 95
            char_threshold = 12 
            if len(text_str) > char_threshold:
                dynamic_font_size = max(50, int(base_font_size * (char_threshold / len(text_str))))
            else:
                dynamic_font_size = base_font_size
            
            try:
                text_shadow = TextClip(text=text_str, font_size=dynamic_font_size, color=(20, 20, 20), font=font_resolved, stroke_color=(0, 0, 0), stroke_width=12, size=box_size, method='label')
                text_front = TextClip(text=text_str, font_size=dynamic_font_size, color='#FFFFFF', font=font_resolved, stroke_color=(40, 40, 40), stroke_width=3, size=box_size, method='label')
            except Exception:
                text_shadow = TextClip(text=text_str, font_size=dynamic_font_size, color='black', size=box_size, method='label')
                text_front = TextClip(text=text_str, font_size=dynamic_font_size, color='white', size=box_size, method='label')
                
            base_y = 1370
            text_shadow = text_shadow.with_duration(duration).with_position(('center', base_y + 8))
            text_front = text_front.with_duration(duration).with_position(('center', base_y))
                         
            gif_clip = (VideoFileClip(bottom_gif_path).resized(width=self.flag_box_size[0], height=self.flag_box_size[1])
                        .with_effects([vfx.Loop(duration=duration)])
                        .with_position(('center', 1570)))
                        
            final_clip = CompositeVideoClip([bg_clip, main_clip, center_clip, text_shadow, text_front, gif_clip])
            
            final_clip.write_videofile(
                output_path, 
                codec='libx264', 
                audio_codec='aac', 
                fps=fps, 
                threads=4,               
                preset='ultrafast', 
                ffmpeg_params=['-crf', '22', '-tune', 'fastdecode'], 
                logger=None
            )
            
            for asset in [bg_clip, main_clip_raw, main_clip, center_clip, text_shadow, text_front, gif_clip, static_mask, final_clip]:
                asset.close()
        except Exception as e:
            raise e
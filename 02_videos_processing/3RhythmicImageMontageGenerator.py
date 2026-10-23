import os
import glob
import cv2
import numpy as np
from moviepy import VideoFileClip

def create_infinity_tunnel_bg(img, width, height):
    """
    Creates a recursive 3D tunnel background by layering 
    smaller, blurred variations of the image behind it.
    """
    base = cv2.resize(img, (width, height), interpolation=cv2.INTER_LINEAR)
    base_blurred = cv2.GaussianBlur(base, (45, 45), 0)
    
    # Layer 3 steps of shrinking frames to simulate a recursive mirror corridor
    for scale in [0.75, 0.5, 0.25]:
        nw, nh = int(width * scale), int(height * scale)
        small = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_CUBIC)
        small_blurred = cv2.GaussianBlur(small, (15, 15), 0)
        
        # Composite center
        ty = (height - nh) // 2
        tx = (width - nw) // 2
        base_blurred[ty:ty+nh, tx:tx+nw] = cv2.addWeighted(
            base_blurred[ty:ty+nh, tx:tx+nw], 0.4, small_blurred, 0.6, 0
        )
    return base_blurred

def apply_vignette(frame):
    """Applies a heavy cinematic vignette mask to darken and blur edges."""
    h, w, _ = frame.shape
    kernel_x = cv2.getGaussianKernel(w, w/2.5)
    kernel_y = cv2.getGaussianKernel(h, h/2.5)
    kernel = kernel_y * kernel_x.T
    mask = kernel / kernel.max()
    
    # Apply to float frame and convert back
    f_frame = frame.astype(np.float32)
    for i in range(3):
        f_frame[:,:,i] *= mask
    return f_frame.astype(np.uint8)

def apply_motion_blur(frame, angle, dist):
    """Applies directional blur to simulate fast camera movement."""
    if dist < 2:
        return frame
    M = cv2.getRotationMatrix2D((dist/2, dist/2), angle, 1)
    kernel = np.zeros((dist, dist))
    kernel[int((dist-1)/2), :] = np.ones(dist)
    kernel = cv2.warpAffine(kernel, M, (dist, dist))
    kernel = kernel / np.sum(kernel)
    return cv2.filter2D(frame, -1, kernel)

def render_max_animation(image_paths, output_video_path, slide_duration=2.2, fps=30):
    """
    Renders images with maximum possible algorithmic VFX: 
    3D Tunnels, Vignettes, Shakes, Flashes, and Motion-Blurred Transitions.
    """
    target_width = 1080
    target_height = 1920
    frames_per_slide = int(slide_duration * fps)
    trans_frames = int(0.25 * fps)  # 0.25-second transition window
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_raw_path = output_video_path.replace(".mp4", "_raw.mp4")
    out = cv2.VideoWriter(temp_raw_path, fourcc, fps, (target_width, target_height))
    
    processed_slides = []
    print("Generating Infinity Tunnel backgrounds & Vignettes...")
    
    for img_path in image_paths:
        img = cv2.imread(img_path)
        if img is None: continue
        
        # Build standard foreground element
        h, w, _ = img.shape
        scale = min(target_width / w, target_height / h)
        nw, nh = int(w * scale), int(h * scale)
        fg_resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_CUBIC)
        
        # Build background framework (Infinity tunnel)
        bg = create_infinity_tunnel_bg(img, target_width, target_height)
        
        # Blend foreground over background tunnel frame
        top = (target_height - nh) // 2
        left = (target_width - nw) // 2
        bg[top:top+nh, left:left+nw] = cv2.addWeighted(
            bg[top:top+nh, left:left+nw], 0.1, fg_resized, 0.9, 0
        )
        
        # Apply dark camera vignette
        final_canvas = apply_vignette(bg)
        processed_slides.append(final_canvas)

    if not processed_slides:
        print("Error: Zero valid images processed.")
        return

    print("Simulating high-energy sequence matrices...")
    clips_timeline = []
    
    for idx, current_canvas in enumerate(processed_slides):
        slide_frames = []
        
        for f in range(frames_per_slide):
            t = f / fps
            progress = f / frames_per_slide
            
            # 1. Advanced Zoom Curve
            if t < 0.12:
                zoom = 1.25 - (0.10 * (t / 0.12)) # Sudden rapid punch-in
            else:
                zoom = 1.15 + (0.05 * progress)   # Slow, lingering crawl
                
            center_x = target_width / 2
            center_y = target_height / 2
            
            # 2. Camera Shake / Vibrational Wobble (First 15% of clip duration)
            if t < 0.15:
                shake_amp = 18 * (1.0 - (t / 0.15))
                center_x += np.random.uniform(-shake_amp, shake_amp)
                center_y += np.random.uniform(-shake_amp, shake_amp)
                
            M = cv2.getRotationMatrix2D((center_x, center_y), 0, zoom)
            frame = cv2.warpAffine(current_canvas, M, (target_width, target_height), flags=cv2.INTER_LINEAR)
            
            # 3. Supercharged Exposure Glow Flash
            flash_dur = 0.3
            if t < flash_dur:
                factor = 2.4 - (1.4 * (t / flash_dur))
                frame = np.clip(frame.astype(np.float32) * factor, 0, 255).astype(np.uint8)
                
            slide_frames.append(frame)
            
        # 4. Motion-Blurred Compound Transitions
        if idx > 0 and len(clips_timeline) > 0:
            prev_slide_frames = clips_timeline[-1]
            vector_direction = idx % 3 # Alternating sliding routes
            
            for f in range(trans_frames):
                alpha = f / trans_frames
                p_frame = prev_slide_frames[-(trans_frames - f)].copy()
                c_frame = slide_frames[f].copy()
                
                # Apply dynamic directional cuts
                if vector_direction == 0:  # Slide Left-to-Right
                    shift = int(target_width * (1 - alpha))
                    p_frame[:, target_width - shift:] = c_frame[:, :shift]
                    p_frame = apply_motion_blur(p_frame, 0, int(45 * (1 - alpha)))
                elif vector_direction == 1: # Slide Right-to-Left
                    shift = int(target_width * (1 - alpha))
                    p_frame[:, :shift] = c_frame[:, target_width - shift:]
                    p_frame = apply_motion_blur(p_frame, 180, int(45 * (1 - alpha)))
                else:                      # Slide Bottom-to-Top
                    shift = int(target_height * (1 - alpha))
                    p_frame[target_height - shift:, :] = c_frame[:shift, :]
                    p_frame = apply_motion_blur(p_frame, 90, int(45 * (1 - alpha)))
                
                # Smooth ghost opacity blending over motion shifts
                blended = cv2.addWeighted(p_frame, 1.0 - (alpha * 0.4), c_frame, alpha * 0.4, 0)
                out.write(blended)
                
            for f in range(trans_frames, frames_per_slide):
                out.write(slide_frames[f])
        else:
            for frame in slide_frames:
                out.write(frame)
                
        clips_timeline.append(slide_frames)

    out.release()
    
    # Pass 3: Transcode via MoviePy container settings
    print("Formatting H.264 profile streams...")
    final_clip = VideoFileClip(temp_raw_path)
    final_clip.write_videofile(output_video_path, codec="libx264", logger=None)
    final_clip.close()
    
    if os.path.exists(temp_raw_path):
        os.remove(temp_raw_path)
    print(f"Process Complete! Max-Effect short output to: {output_video_path}")

if __name__ == "__main__":
    input_directory = os.path.join("02_videos_processing", "inputs", "images")
    output_file = os.path.join("02_videos_processing", "outputs","2025_Ranking_Cutoff.mp4")
    
    extensions = ('*.jpg', '*.jpeg', '*.png', '*.webp')
    target_paths = []
    for ext in extensions:
        target_paths.extend(glob.glob(os.path.join(input_directory, ext)))
    target_paths.sort()
    
    if target_paths:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        # 30 FPS gives silky smooth motion blurs and camera shakes
        render_max_animation(target_paths, output_file, slide_duration=2.1, fps=60)
    else:
        print(f"Error: Missing image components inside {input_directory}")
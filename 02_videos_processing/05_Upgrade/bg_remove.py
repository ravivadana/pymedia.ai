import cv2
from rembg import remove
from PIL import Image
import numpy as np
from tqdm import tqdm

input_video = "02_videos_processing/05_Upgrade/input_normal4k.mp4"
output_video = "02_videos_processing/05_Upgrade/output_no_bg.mp4"

# 1. Open the video file
cap = cv2.VideoCapture(input_video)
if not cap.isOpened():
    print("Error: Could not open input video.")
    exit()

# 2. Get original video properties
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# 3. Setup Video Writer
# Note: Using 'mp4v' for standard MP4. If you want a truly transparent background,
# you would need an alpha channel codec like 'png ' or 'HEVC/VP9', but black is the standard fallback.
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

print(f"Processing {total_frames} frames. AI model loading...")

# 4. Loop through every frame with a progress bar
for _ in tqdm(range(total_frames)):
    ret, frame = cap.read()
    if not ret:
        break

    # OpenCV reads in BGR, rembg needs RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(frame_rgb)

    # Apply AI background removal
    # This returns an RGBA image (Alpha channel contains transparency)
    output_pil = remove(pil_img)
    
    # Convert back to numpy array
    output_numpy = np.array(output_pil)

    # If background is transparent, convert transparent pixels to black for standard MP4 container
    if output_numpy.shape[2] == 4:  # Has RGBA channels
        # Create a black background mask
        black_bg = np.zeros((height, width, 3), dtype=np.uint8)
        alpha = output_numpy[:, :, 3] / 255.0
        alpha = np.expand_dims(alpha, axis=2)
        
        # Extract RGB channels
        rgb_channels = output_numpy[:, :, :3]
        
        # Blend the foreground with the black background
        final_frame = (rgb_channels * alpha + black_bg * (1 - alpha)).astype(np.uint8)
    else:
        final_frame = output_numpy

    # Convert RGB back to BGR for OpenCV output
    final_frame_bgr = cv2.cvtColor(final_frame, cv2.COLOR_RGB2BGR)
    out.write(final_frame_bgr)

# Release resources
cap.release()
out.release()
cv2.destroyAllWindows()

print(f"\nFinished! Background removed video saved as: {output_video}")
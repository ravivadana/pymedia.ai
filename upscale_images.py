# --- Your regular imports ---
import cv2
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
# ... rest of the code ...

import os
import glob
import cv2
from basicsr.archs.rrdbnet_arch import RRDBNet

# --- Configuration ---
INPUT_FOLDER = r"C:\Ravi\Python\2025\Media\02_videos_processing\05_Upgrade\inputs/images"
OUTPUT_FOLDER = r"C:\Ravi\Python\2025\Media\02_videos_processing\05_Upgrade\outputs/images"

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialize Real-ESRGAN Architecture
# RRDBNet is the backbone of Real-ESRGAN
model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)

# Create the Upscaler Instance
upscaler = RealESRGANer(
    scale=4,
    model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth', # Automatically downloads on first run
    model=model,
    tile=400,          # Built-in tiling: processes image in 400x400 blocks to prevent memory crashes
    tile_pad=10,       # Padding to prevent visible seams/lines between tiled blocks
    pre_pad=0,
    half=False         # Set to True ONLY if you have an NVIDIA GPU with CUDA installed
)

# Find all images in the input folder
extensions = ('*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp')
image_paths = []
for ext in extensions:
    image_paths.extend(glob.glob(os.path.join(INPUT_FOLDER, ext)))
    image_paths.extend(glob.glob(os.path.join(INPUT_FOLDER, ext.upper())))

if not image_paths:
    print(f"No images found in '{INPUT_FOLDER}'.")
    exit()

print(f"Found {len(image_paths)} images. Starting Real-ESRGAN upscaling...")

# Process loop
for img_path in image_paths:
    filename = os.path.basename(img_path)
    print(f"Processing: {filename}...")
    
    img = cv2.imread(img_path)
    if img is None:
        print(f" Failed to read {filename}. Skipping.")
        continue
    
    try:
        # Run Real-ESRGAN upscaling
        # outscale=4 means the final output is 4x larger
        upscaled_img, _ = upscaler.enhance(img, outscale=4)
        
        # Save the result
        output_path = os.path.join(OUTPUT_FOLDER, filename)
        cv2.imwrite(output_path, upscaled_img)
        print(f" Saved upscaled image to {output_path}")
        
    except Exception as e:
        print(f" Failed to process {filename}. Error: {e}")

print(f"\nFinished! All high-definition upscaled images are in: {OUTPUT_FOLDER}")
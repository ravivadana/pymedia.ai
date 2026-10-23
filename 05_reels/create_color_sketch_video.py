import cv2
import numpy as np

def convert_to_cartoon_sketch(frame):
    # --- Step 1: Generate Bold Cartoon Outlines ---
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Apply median blur to reduce noise before finding edges
    gray_blurred = cv2.medianBlur(gray, 7)
    
    # Use adaptive thresholding to detect sharp, bold edges (like a comic book)
    # Block size (9) and constant subtraction (2) control edge thickness and sensitivity
    edges = cv2.adaptiveThreshold(
        gray_blurred, 255, 
        cv2.ADAPTIVE_THRESH_MEAN_C, 
        cv2.THRESH_BINARY, 9, 2
    )
    
    # --- Step 2: Create Flattened Cartoon Colors ---
    # Bilateral filter clears textures (like skin pores or wall grains) 
    # but strictly preserves strong color boundaries. 
    # Running it iteratively enhances the flat, painted cartoon look.
    color_smoothed = frame.copy()
    for _ in range(3):
        color_smoothed = cv2.bilateralFilter(color_smoothed, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Optional: Quantize colors (Posterization) to enforce blocky colors
    # Uncomment the lines below if you want an even flatter comic-book palette:
    # n_colors = 8
    # data = color_smoothed.astype(np.float32)
    # color_smoothed = np.floor(data / (256 / n_colors)) * (256 / n_colors) + (256 / (2 * n_colors))
    # color_smoothed = color_smoothed.astype(np.uint8)

    # --- Step 3: Combine Edges and Flattened Colors ---
    # Convert the single-channel edges back to BGR format
    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    # Bitwise AND merges them: where the edge mask is black (0), it draws a black outline.
    # Where the edge mask is white (255), it retains the smooth color.
    cartoon_frame = cv2.bitwise_and(color_smoothed, edges_bgr)
    
    return cartoon_frame

def process_video(input_path, output_path):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Error: Could not open input video.")
        return

    # Extract video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Set up the writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    print("Processing cartoon sketch animation...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Transform frame into cartoon sketch
        cartoon_frame = convert_to_cartoon_sketch(frame)
        
        # Write to final video file
        out.write(cartoon_frame)
        
    cap.release()
    out.release()
    print(f"Finished! Cartoon sketch video saved to: {output_path}")

# Run the program
input_video = "05_reels/inputs/original_video1.mp4"   # Your input video name
output_video = "05_reels/outputs/original_video1_cartoon_sketch.mp4"    # Your output video name

process_video(input_video, output_video)
import cv2
import numpy as np

def convert_to_sketch(frame):
    # Step 1: Convert to grayscale
    gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Step 2: Invert the grayscale image
    inverted_img = cv2.bitwise_not(gray_img)
    
    # Step 3: Apply Gaussian Blur to the inverted image
    # A larger kernel size (e.g., 21x21) yields a softer, more detailed sketch
    blurred_img = cv2.GaussianBlur(inverted_img, (21, 21), sigmaX=0, sigmaY=0)
    
    # Step 4: Blend the gray image with the blurred image using Color Dodge
    sketch = cv2.divide(gray_img, 255 - blurred_img, scale=256.0)
    
    # Convert back to BGR format so it can be written to the output video
    return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

def process_video(input_path, output_path):
    # Open the original video
    cap = cv2.VideoCapture(input_path)
    
    if not cap.isOpened():
        print("Error: Could not open input video.")
        return

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Define the codec and create VideoWriter object
    # 'mp4v' works well for .mp4 files across most systems
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    print("Processing video frames... Please wait.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break  # End of video
            
        # Apply the sketch effect to the current frame
        sketch_frame = convert_to_sketch(frame)
        
        # Write the processed frame to the output file
        out.write(sketch_frame)
        
    # Release everything when the job is finished
    cap.release()
    out.release()
    print(f"Success! Sketch video saved to: {output_path}")

# Run the processing
input_video = "05_reels/master.mp4"   # Path to your input video
output_video = "05_reels/outputs/master_sketch_video.mp4"    # Path where you want to save the sketch video

process_video(input_video, output_video)
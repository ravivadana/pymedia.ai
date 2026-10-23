import cv2


def cartoonize_video(input_path, output_path):
    # 1. Open the source video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Error: Could not open input video.")
        return

    # Get video properties for the output writer
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Define the codec and create VideoWriter object
    # 'mp4v' is widely supported for MP4 files
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    print(f"Processing {total_frames} frames. Please wait...")

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # --- CARTOON EFFECT PIPELINE ---

        # Step A: Get prominent edges
        # Convert to grayscale and blur to remove minor noise
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.medianBlur(gray, 5)

        # Adaptive thresholding creates clean, pencil-like outlines
        edges = cv2.adaptiveThreshold(
            gray_blur,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            blockSize=9,
            C=9,
        )

        # Step B: Flatten the colors
        # Bilateral filter reduces noise while keeping crisp boundaries
        color = cv2.bilateralFilter(frame, d=9, sigmaColor=300, sigmaSpace=300)

        # Step C: Combine edges and color
        # Convert edges back to BGR color space so we can bitwise-AND it with the color frame
        cartoon_frame = cv2.bitwise_and(color, color, mask=edges)

        # --- END PIPELINE ---

        # Write the processed frame to the output file
        out.write(cartoon_frame)

        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Progress: {frame_count}/{total_frames} frames processed.")

    # Clean up and release everything
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Success! Cartoon video saved to: {output_path}")


# --- Execution ---
if __name__ == "__main__":
    # Replace these with your actual file paths
    input_video = f"02_videos_processing/06_REELS/djnusakami.mp4"
    output_video = f"02_videos_processing/06_REELS/djnusakami_cartoon_output.mp4"

    cartoonize_video(input_video, output_video)
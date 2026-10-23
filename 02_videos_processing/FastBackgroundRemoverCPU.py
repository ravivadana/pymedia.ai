import os
import cv2
import numpy as np
from rembg import remove, new_session
from tqdm import tqdm   # progress bar (recommended)

# If you want to use your own custom ProgressBar:
# from progress_bar import ProgressBar

class FastBackgroundRemoverCPU:
    def __init__(self):
        print("⏳ Loading FAST model (u2netp)...")
        self.session = new_session("u2netp")   # fastest CPU model
        print("🚀 Model loaded (CPU optimized).")

    def remove_frame(self, frame_bgr):
        # Convert frame BGR → RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # Encode directly to PNG bytes (faster than PIL)
        success, encoded = cv2.imencode(".png", frame_rgb)
        if not success:
            return frame_bgr
        
        # Run the fast model
        result_bytes = remove(encoded.tobytes(), session=self.session)

        # Decode bytes → np array
        result_np = cv2.imdecode(
            np.frombuffer(result_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        return result_np

    def remove_video_bg(self, input_video_path, frame_skip=1):
        output_path = input_video_path.replace(".mp4", "_bgr.mp4")

        cap = cv2.VideoCapture(input_video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        out = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps, (w, h)
        )

        print(f"\n🎞 Total frames: {total_frames}")
        print(f"⏩ Frame skip: {frame_skip}")

        # tqdm progress bar
        pbar = tqdm(total=total_frames, desc="Processing", unit="frame")

        frame_id = 0
        last_frame = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_id % frame_skip == 0:
                last_frame = self.remove_frame(frame)

            out.write(last_frame)

            frame_id += 1
            pbar.update(1)

        cap.release()
        out.release()
        pbar.close()

        print("\n✅ Completed with FAST CPU optimization.")
        return output_path


# if __name__ == "__main__":
#     input_video_path = "inputs/videos/Chandanathin/000.mp4"

#     remover = FastBackgroundRemoverCPU()
#     remover.remove_video_bg(input_video_path, frame_skip=1)

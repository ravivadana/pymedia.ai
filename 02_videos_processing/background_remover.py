import os
import cv2
import numpy as np
from rembg import remove, new_session
from tqdm import tqdm


class BackgroundRemover:
    def __init__(self, model_name="u2net"):
        # Reuse session for speed (VERY IMPORTANT)
        self.session = new_session(model_name)

    def remove_video_bg(self, input_video_filepath):
        output_file_path = input_video_filepath.replace(".mp4", "_bgr.mp4")

        cap = cv2.VideoCapture(input_video_filepath)
        if not cap.isOpened():
            raise Exception("Could not open video file")

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_file_path, fourcc, fps, (width, height))

        print("Processing video...")

        with tqdm(total=total_frames) as pbar:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Convert BGR → RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Direct numpy processing (no PNG conversion)
                result = remove(frame_rgb, session=self.session)

                # Convert back to BGR
                result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)

                out.write(result_bgr)
                pbar.update(1)

        cap.release()
        out.release()

        print("✅ Background removed successfully.")
        return output_file_path


if __name__ == "__main__":
    input_video_folder = "02_videos_processing/inputs/videos"
    input_video_filename = "ar_bg2.mp4"
    input_video_filepath = f"{input_video_folder}/{input_video_filename}"

    os.makedirs(input_video_folder, exist_ok=True)

    remover = BackgroundRemover()
    remover.remove_video_bg(input_video_filepath)

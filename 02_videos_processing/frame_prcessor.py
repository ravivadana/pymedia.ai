import cv2
import os
from rembg import remove
from PIL import Image
from tqdm import tqdm
from rembg import remove
from video_creater import VideoCreator
from progress_bar import ProgressBar
import threading
import sys
from pathlib import Path
class FrameProcessor:
    def extract_frames_from_mp4(self,input_video,frames_dir):
        print("extract frames from mp4 file started")
        cap = cv2.VideoCapture(input_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print("Extracting frames...")
        progressBar=ProgressBar()
        i = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imwrite(f"{frames_dir}/{i:06}.png", frame)
            i += 1
            progressBar.progress(i, frame_count)
        cap.release()
        print("extract frames from mp4 file completed")
        return frames_dir

    def create_background_removed_frames(self,frames_dir,processed_dir, chunks):
        for chunk in chunks:
            with open(f'{frames_dir}/{chunk}', 'rb') as i:
                with Image.open(i) as img:
                    output_image = remove(img)
                    output_image.save(f'{processed_dir}/{chunk}')

if __name__=="__main__":
    frameProcessor=FrameProcessor()
    input_folder="inputs/videos"
    input_video=f"{input_folder}/11.mp4"
    file_name=Path(input_video).stem
    frames_dir=f"{input_folder}/frames"
    os.makedirs(frames_dir, exist_ok=True)
    processed_dir=f"{frames_dir}/processed"
    os.makedirs(processed_dir, exist_ok=True)
    frames_dir=frameProcessor.extract_frames_from_mp4(input_video,frames_dir)
     # --- Process frames ---
    print("Preparing chuncks for parallel processing")
    frame_file_names = sorted(os.listdir(frames_dir))
    processed_file_names = sorted(os.listdir(processed_dir))
    frame_file_names=list(set(frame_file_names) - set(processed_file_names))
    chunk_size = 100
    chunks = [frame_file_names[i:i + chunk_size] for i in range(0, len(frame_file_names), chunk_size)]

    threads = []
    results = [None] * len(chunks)
    chunks_count=len(chunks)
    print("Background removing from frames started")
    for i, chunk in enumerate(chunks):
            # Create a thread for each chunk
        thread = threading.Thread(target=frameProcessor.create_background_removed_frames, args=(frames_dir,processed_dir, chunk))
        threads.append(thread)
        thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        print(f"{i} th chunk completed")

    print("Background removing from frames completed")
    videoCreator=VideoCreator()
    videoCreator.create_mp4_from_png(f'{processed_dir}',f'{processed_dir}/{file_name}.mp4')
    print("Processed output file created")
        

        

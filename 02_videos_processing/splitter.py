import subprocess
import math
import re
import os
from pathlib import Path
import shutil

class Splitter:
    def get_video_duration(self,filename):
        """Retrieves the duration of a video file using FFmpeg."""
        cmd = ["ffmpeg", "-i", filename]
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
        stderr = process.communicate()[1]
        
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.\d+", stderr)
        if match:
            hours, minutes, seconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds
        return None

    def split_video_subprocess(self,input_file,output_folder, chunk_duration_seconds):
        video_length = self.get_video_duration(input_file)
        if video_length is None:
            print("Could not determine video length.")
            return
        os.makedirs(output_folder, exist_ok=True)
        num_chunks = math.ceil(video_length / chunk_duration_seconds)

        for i in range(0,num_chunks):
            start_time = i * chunk_duration_seconds
            output_file = f"{output_folder}/{str(i).zfill(3)}.mp4"
            
            cmd = [
                "ffmpeg",
                "-ss", str(start_time),
                "-i", input_file,
                "-t", str(chunk_duration_seconds),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                output_file
            ]
            
            try:
                subprocess.run(cmd, check=True)
                print(f"Created chunk: {output_file}")
            except subprocess.CalledProcessError as e:
                print(f"Error creating chunk {output_file}: {e}")
            
        return output_folder


# # Example usage:
# output_folder='inputs/videos'
# input_video = f'{output_folder}/Chandanathin Manamulla ｜ M G Sreekumar ｜ Dakshina Ganga ｜ Dance Cover ｜ Ganga S ｜  #shorts.mp4'  # Replace with your video file
# file_name_without_extension = Path(input_video).stem
# output_chunks_folder=f'{output_folder}/{file_name_without_extension}'
# folder_to_delete = output_chunks_folder  # Replace with the actual path
# if os.path.isdir(folder_to_delete):
#     shutil.rmtree(folder_to_delete)
# split_duration = 15  # Split into 60-second chunks
# splitter=Splitter()
# splitter.split_video_subprocess(input_video, output_chunks_folder, split_duration)
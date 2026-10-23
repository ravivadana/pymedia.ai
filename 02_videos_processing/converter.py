import subprocess
import os
import threading
from audio_video_extractor import AudioVideoExtractor
class Converter:
    def convert_to_mp4(self,input_file, output_file):
        command = [
                'ffmpeg',
                '-i', input_file,
                '-c:v', 'libx264',  # Video codec for MP4
                '-crf', '23',       # Constant Rate Factor for quality (lower is better)
                '-preset', 'medium', # Encoding speed vs. compression efficiency
                '-c:a', 'aac',       # Audio codec for MP4
                '-b:a', '128k',      # Audio bitrate
                output_file
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Successfully converted '{input_file}' to '{output_file}'")
        except subprocess.CalledProcessError as e:
            print(f"Error during conversion: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            print(f"failed in converting {input_file}")
            if os.path.exists(input_file):
                os.remove(input_file)
        except FileNotFoundError:
            print("FFmpeg not found. Please ensure FFmpeg is installed and accessible in your system's PATH.")
        if os.path.exists(input_file):
            os.remove(input_file)
        return output_file
    
    def convert_all_web_to_mp4(self,inputput_video_folder):
        file_names = sorted(os.listdir(inputput_video_folder))
        output_videos_folder=inputput_video_folder
        file_names = sorted(
                    f for f in os.listdir(inputput_video_folder) if f.endswith(".webm")
                )
        output_path="inputs/videos"
        for item in file_names:
            input_file_path=f'{inputput_video_folder}/{item}'
            output_file_path=f'{inputput_video_folder}/{item.replace(".webm",".mp4")}'
            self.convert_to_mp4(input_file_path,output_file_path)
        print("Convertion complted")


# # Single file:
# input_filename="adi_avvadamma.webm"
# inputs_folder=f"inputs/videos"
# current_working_dir = "videos_processing"
# input_filepath=f'{current_working_dir}/{inputs_folder}/{input_filename}'
# root, extension = os.path.splitext(input_filepath)
# file_name_without_extension = os.path.basename(root)
# output_filename=f'{file_name_without_extension}.mp4'
# outputs_folder=f"{current_working_dir}/outputs"
# output_filepath=f'{outputs_folder}/{output_filename}'
# converter=Converter()
# converter.convert_to_mp4(input_filepath, output_filepath)

# # convert mutiple files from webm to mp4
# if __name__ == "__main__":
#     current_working_dir = "videos_processing"
#     inputput_video_folder = f"{current_working_dir}/inputs/videos"
#     file_names = sorted(os.listdir(inputput_video_folder))
#     output_videos_folder=inputput_video_folder
#     os.makedirs(output_videos_folder, exist_ok=True)
#     converter=Converter()
#     threads = []
#     output_path="inputs/videos"
#     for item in file_names:
#         input_file_path=f'{inputput_video_folder}/{item}'
#         output_file_path=f'{inputput_video_folder}/{item.replace(".webm",".mp4")}'
#         t = threading.Thread(target=converter.convert_to_mp4, args=(input_file_path,output_file_path,))
#         threads.append(t)
#         t.start()

#     #block until all the threads finish (i.e. until all function_a functions finish)    
#     for t in threads:
#         t.join()
#     print("Convertion complted")
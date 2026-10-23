from moviepy import VideoFileClip
import os
from pathlib import Path
import threading
class AudioVideoExtractor:
    def extract_video(self,input_video_file_path,output_video_filename):
        video_clip = VideoFileClip(input_video_file_path)
        video_only_clip = video_clip.without_audio()
        video_only_clip.write_videofile(output_video_filename, codec='libx264')
        video_only_clip.close()
        video_clip.close()
        print(f"Video-only file created: {output_video_filename}")
        return output_video_filename
    
    def extract_audio(self,input_video_filepath,output_video_filename):
        if(os.path.exists(input_video_filepath)):
            video_clip = VideoFileClip(input_video_filepath)
            audio_clip = video_clip.audio
            audio_extension="mp3"
            audio_clip.write_audiofile(output_video_filename, codec=audio_extension)
            audio_clip.close()
            video_clip.close()
            print(f"Audio extracted to: {output_video_filename}")
        else:
            print(f"input file {output_video_filename}  not found")
            
        return output_video_filename
        
# # to download video from singl youtube instagram url
# if __name__ == "__main__":
#     mediaExtractor=AudioVideoExtractor()
#     input_videos_folder="inputs/videos"
#     input_file="Swami Ayyappa⚜️📿#trending #dance #sabarimalai #ayyappaswamy #ayyappaswamytemple #dance #twindancer.mp4"
#     input_videos_file_path=f"{input_videos_folder}/{input_file}"
#     print("Extract video and autio Started")
#     input_file_path=f"{input_videos_folder}/{input_file}"
#     video_only_file=mediaExtractor.extract_video(input_file_path,input_file_path.replace(".mp4","_video_only.mp4"))
    
#     input_audios_folder="inputs/audios"
#     os.makedirs(input_audios_folder, exist_ok=True)
#     output_audio_file_path=f"{input_audios_folder}/{input_file}".replace(".mp4",".mp3")
#     audio_output_filename=mediaExtractor.extract_audio(input_videos_file_path,output_audio_file_path)

#generate audio and video only files

# #multiple files video and audio extract
# if __name__ == "__main__":
#     inputput_video_folder = "inputs/videos"
#     input_audios_folder="inputs/audios"
#     os.makedirs(input_audios_folder, exist_ok=True)
#     file_names = sorted(os.listdir(inputput_video_folder))
#     output_videos_folder=inputput_video_folder
#     os.makedirs(output_videos_folder, exist_ok=True)
#     mediaExtractor=AudioVideoExtractor()
#     video_only_threads = []
#     for item in file_names:
#         input_file_path=f'{inputput_video_folder}/{item}'
#         output_video_only_file_path=input_file_path.replace(".mp4","_video_only.mp4")
#         video_only_thread = threading.Thread(target=mediaExtractor.extract_video, args=(input_file_path,output_video_only_file_path,))
#         video_only_threads.append(video_only_thread)
#         video_only_thread.start()
#     # block until all the threads finish (i.e. until all function_a functions finish)    
#     for video_only_thread in video_only_threads:
#         video_only_thread.join()
#     print("Videos only completed")

#     audio_only_threads = []
#     for item in file_names:
#         input_file_path=f'{inputput_video_folder}/{item}'
#         output_audios_folder="inputs/audios"
#         output_audio_only_file_path=f"{output_audios_folder}/{item}".replace(".mp4",".mp3")
#         audio_only_thread = threading.Thread(target=mediaExtractor.extract_audio, args=(input_file_path,output_audio_only_file_path,))
#         audio_only_threads.append(audio_only_thread)
#         audio_only_thread.start()
#     # block until all the threads finish (i.e. until all function_a functions finish)    
#     for audio_only_thread in audio_only_threads:
#         audio_only_thread.join()
#     print("Audios only completed")
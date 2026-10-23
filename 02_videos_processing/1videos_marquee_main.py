from yt_downloader import MediaDownLoader
from videos_marquee_resize import VideosMarqueeResize
from folder_sanitize import FolderSanitizer
import glob
import os
import shutil
from converter import Converter

def download_video_from_url(video_url,inputput_video_folder):
    print("downloading video Started")
    mediaDownLoader=MediaDownLoader()
    downloaded_video_file=mediaDownLoader.download_video_with_ytdlp(inputput_video_folder,video_url)
    print("downloading video Completed")
    return downloaded_video_file
def archive_files(source_folder):
    archive_folder="02_videos_processing/archive"
    if not os.path.exists(archive_folder):
        os.makedirs(archive_folder)
    if os.path.exists(source_folder):
        for filename in os.listdir(source_folder):
            source_path = os.path.join(source_folder, filename)
            destination_path = os.path.join(archive_folder, filename)
            try:
                shutil.move(source_path, destination_path) # If destination_dir is a directory, the file moves inside it
                print(f"Moved {filename} to {archive_folder}")
            except shutil.Error as e:
                print(f"Error moving {filename}: {e}")

if __name__=="__main__":
    processing_folder="02_videos_processing"
    videos_input_folder=f"{processing_folder}/inputs/videos"
    output_folder=f"{processing_folder}/outputs"
    direction="up"
    archive_files(videos_input_folder)
    archive_files(output_folder)
    video_urls=[
                'https://www.youtube.com/shorts/7AFLp8aVNKU',
                'https://www.youtube.com/shorts/HTE8HuuNy6Q',
                'https://www.youtube.com/shorts/4GvDaGRwNn8',
                'https://www.youtube.com/shorts/tF9P5R7JzL8',
                'https://www.youtube.com/shorts/QJsUc_vYAig',
                'https://www.youtube.com/shorts/QJsUc_vYAig'
                ]
    for video_url in video_urls:
        downloaded_video_file=download_video_from_url(video_url,videos_input_folder)
        data={"downloaded_video_file":downloaded_video_file }
    print("completed all files downloaded")

    converter=Converter()
    converter.convert_all_web_to_mp4(videos_input_folder)

    videosMarquee=VideosMarqueeResize()
    caption_text=r"ఎన్నీయల్లో ఒళ్ళో పూల జాల్లో \n మల్లియల్లో తల్లో వాన విల్లో \n ఎన్నీయల్లో ఒళ్ళే చెమ్మ గిల్లో \n మల్లియల్లో మంచే తేనె జాల్లో \n ఒల్లోకొస్తే వయ్యారాలు \n ఇల్లోకొస్తే సంసారాలు \n పగలే తారలు \n \n ఎన్నీయల్లో ఒళ్ళో పూల జాల్లో \n మల్లియల్లో తల్లో వాన విల్లో \n ఎన్నీయల్లో ఒళ్ళే చెమ్మ గిల్లో \n మల్లియల్లో మంచే తేనె జాల్లో"
    font_path=f"C:/Ravi/Python/2025/Media/assets/fonts/Lohit Telugu Regular.ttf"
    final_video=videosMarquee.create_marquee_video(videos_input_folder,output_folder,direction, caption_text,font_path)
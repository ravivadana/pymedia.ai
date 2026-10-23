import subprocess
import os
import glob
import re
import shutil
from yt_downloader import MediaDownLoader
from videos_grid_view_max_duration import VideosGridView

def download_video_from_url(video_url,inputput_video_folder):
    print("downloading video Started")
    mediaDownLoader=MediaDownLoader()
    downloaded_video_file=mediaDownLoader.download_video_with_ytdlp(inputput_video_folder,video_url)
    print("downloading video Completed")
    return downloaded_video_file
def archive_files(source_folder):
    archive_folder="archive"
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
# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    videos_input_folder = "02_videos_processing/inputs/videos"
    output_folder = "02_videos_processing/outputs"

    # #Archive old files
    archive_files(videos_input_folder)
    archive_files(output_folder)

    #Download new videos
    video_urls = [
          'https://www.youtube.com/shorts/p1LqB1ImeX4',
                                'https://www.youtube.com/shorts/YCZncR5llE4',
                                'https://www.youtube.com/shorts/ukF8lk7IYzE',
                                'https://www.youtube.com/shorts/MLrTtJ9Bv-Q',
                                'https://www.youtube.com/shorts/sQceRMSqJjE',
                                'https://www.youtube.com/shorts/5OThW9dYVtI',
                                'https://www.youtube.com/shorts/bIR7XB1_nPo',
                                'https://www.youtube.com/shorts/NCl0vtYLeuo',
                                'https://www.youtube.com/shorts/vCVaNVeLyGM',
                                'https://www.youtube.com/shorts/4HNuGS9tFac',
                                'https://www.youtube.com/shorts/AHQFg3k078I?si=EOCuLoCzo77m40FX',
                                'https://www.youtube.com/shorts/7iJWAeHNYkE'
    ]

    for video_url in video_urls:
        download_video_from_url(video_url, videos_input_folder)

    videosGridView=VideosGridView()

    canvas_width=1080,
    canvas_height=1920
    final_video=videosGridView.create_video(canvas_width,canvas_height,videos_input_folder,output_folder)
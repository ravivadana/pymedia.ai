import json
from yt_downloader import MediaDownLoader
import os
from datetime import datetime
mediaDownLoader=MediaDownLoader()
output_video_folder="background_theme_videos"
os.makedirs(output_video_folder, exist_ok=True)
with open("download_links.json") as json_file:
    json_data = json.load(json_file)
    print(json_data)
    now = datetime.now()
    for link in json_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name_part=timestamp
        mediaDownLoader.download_video_with_ytdlp(link,output_video_folder,file_name_part)
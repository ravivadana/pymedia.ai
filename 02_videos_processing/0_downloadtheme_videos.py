from yt_downloader import MediaDownLoader
from videos_marquee_resize import VideosMarqueeResize
from folder_sanitize import FolderSanitizer
import glob
import os
import shutil
from converter import Converter
import time
import threading

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
    videos_input_folder=r"C:\Ravi\Python\2025\Media\background_theme_videos\2026_10_01"
    direction="up"
    video_urls=[
                'https://www.instagram.com/reel/DbuVdmFt-Hv/?stkn=MWw2b2dobzBubGNjdg%3D%3D',
                'https://www.instagram.com/reel/Dd2rYX3NQ0Q/?stkn=MW45ZzM5bDlyc3A2Nw%3D%3D',
                'https://www.instagram.com/reel/DbiOFKeNhen/?stkn=MXA4eGk2eXk2cmtjZg%3D%3D',
                'https://www.instagram.com/reel/DcxRx_Sjnq9/?stkn=MTh0YWk4MHE1bHlwMg%3D%3D',
                'https://www.instagram.com/reel/DcRF9Uuu19K/?stkn=MXNzb2xtOWx6MDkzcg%3D%3D',
                'https://www.instagram.com/reel/Dd1Nc6Aupti/?stkn=MXJsYzJ5YTAxeTVuaw%3D%3D',
                'https://www.instagram.com/reel/DYUtPUKhWB4/?stkn=eGM3NHRraTlkdmU4',
                'https://www.instagram.com/reel/Dd24fQdtUoU/?stkn=ZjdxaGk4aHlkcTVu',
                'https://www.instagram.com/reel/DbpWH9UNJko/?stkn=MWd0eWY2dGgyYmV4aQ%3D%3D',
                'https://www.instagram.com/reel/DXHR-fEj0JS/?stkn=MTgwcWZuc3U1NnZpdA%3D%3D',
                'https://www.instagram.com/reel/DbQhSiHNLFx/?stkn=MTFtbGx4d3dpc2Y4Zw%3D%3D',
                'https://www.instagram.com/reel/DcMlqCQNUKL/?stkn=bGUxNnBidGk4bWoy',
                'https://www.instagram.com/reel/Dc840gjNnJg/?stkn=dmJ5NjRvZjBub2h0',
                'https://www.instagram.com/reel/DcgS7Y-Pn-U/?stkn=ZWEzZDl2eGQyZ3ls',
                'https://www.instagram.com/reel/DXp8MDqERBH/?stkn=NXpzbHRiNjQxOG1p',
                'https://www.instagram.com/reel/Dd1W6tcAxx7/?stkn=MTlpNTNva2UzMGwwMw%3D%3D',
                'https://www.instagram.com/reel/DdK0c_0t6qo/?stkn=ZmdpbWh1eW12NWQ%3D',
                'https://www.instagram.com/reel/DbsJyVSu4EB/?stkn=MXJuZXNlZzFuZGFscw%3D%3D',
                'https://www.instagram.com/reel/DbK2V6sOQlP/?stkn=MTN1OXMyNXJtNmIzeA%3D%3D',
                'https://www.instagram.com/reel/Dc6XGDCtAfB/?stkn=MWN6cm13MmY5a2J1OQ%3D%3D',
                'https://www.instagram.com/reel/DdKixkUlAOG/?stkn=MWZnNzI0andqZHI3cA%3D%3D',
                'https://www.instagram.com/reel/DayF2Vhiiur/?stkn=MTZ1cXFqc3FzZWU5ZA%3D%3D',
                'https://www.instagram.com/reel/Dbs0KAyuy0H/?stkn=d3V3MjZrcmgxbGhy',
                'https://www.instagram.com/reel/DdxkZfdhVgK/?stkn=MWdmdmMydHd5bDFweg%3D%3D',
                'https://www.instagram.com/reel/DcjQDEuIzNd/?stkn=M2IyaHdldm8zOWR5',
                'https://www.instagram.com/reel/Dau1ZlyRLt3/?stkn=MXdyMzlma2Y4N3E3eQ%3D%3D',
                'https://www.instagram.com/reel/DaIZ3P4BQEH/?stkn=ajhhZGo0eHd1MXpo',
                'https://www.instagram.com/reel/DZr_VlmxsNt/?stkn=amxoa2wzZXNuMjlx',
                'https://www.instagram.com/reel/DZr_VlmxsNt/?stkn=amxoa2wzZXNuMjlx',
                'https://www.instagram.com/reel/Ddv_NJ-E2y_/?stkn=MWhnOTJhMThueTRneA%3D%3D',
                'https://www.instagram.com/reel/DcymiP3t49_/?stkn=Z2E5OXp3aTJpM2E4',
                'https://www.instagram.com/reel/Ddx6Xn1zbPy/?stkn=bHZ5aXdrZTBqM2xi',
                'https://www.instagram.com/reel/DbQQ6oFsY4v/?stkn=MWl1MndiMmFpMXdobQ%3D%3D',
                'https://www.instagram.com/reel/DZNYDtZt6Id/?stkn=b254ZGRuZnF6ZmI0',
                'https://www.instagram.com/reel/DccMX7OlTK6/?stkn=a2Vka3pzYmY2YTA3',
                'https://www.instagram.com/reel/DaF-57GPaxS/?stkn=eDc0ejRkZm9jenV3',
                'https://www.instagram.com/reel/Ddt-_7qAgQM/?stkn=MWhmYWpreDQ3eXZraA%3D%3D',
                'https://www.instagram.com/reel/Dcp5tKMiZZm/?stkn=NnNkZGpqeHo2YXNu',
                'https://www.instagram.com/reel/DdjlAwdDehc/?stkn=MThuMWt5eWl1OHpsbw%3D%3D',
                'https://www.instagram.com/reel/DdBr04PM2kW/?stkn=MTJrdmxyMXE1OTczdg%3D%3D',
                'https://www.instagram.com/reel/DdAwLToGrcT/?stkn=MnY5cWtveGd2c3hy',
                'https://www.instagram.com/reel/DdEv1owt4gX/?stkn=MXFpYXNldnNuMm4xYg%3D%3D',
                'https://www.instagram.com/reel/DdEACGaxPP9/?stkn=MzI5eHBxcXpzdGl4',
                'https://www.instagram.com/reel/DcQEfToOeiW/?stkn=MWJueGQxaXRhbG1mOQ%3D%3D',
                'https://www.instagram.com/reel/DcIkgBWggU2/?stkn=Z3YwMG44MXFqZ2tq',
                'https://www.instagram.com/reel/DYSImeWNqEl/?stkn=MTZuaWlieWtyY2x4cA%3D%3D',
                'https://www.instagram.com/reel/DcWEN7Mpzjm/?stkn=MTExNnN1M3o1a2prMw%3D%3D',
                'https://www.instagram.com/reel/DcUyjemxI4o/?stkn=MjMzNXEyd2d3M2p1',
                'https://www.instagram.com/reel/DZ70AE_teS0/?stkn=ZTRqdno1bTBrdnR2'
                ]
    for video_url in video_urls:
        downloaded_video_file=download_video_from_url(video_url,videos_input_folder)
        data={"downloaded_video_file":downloaded_video_file }
        time.sleep(5)
    print("completed all files downloaded")

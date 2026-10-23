import os
from pathlib import Path
from yt_downloader import MediaDownLoader
from audio_video_extractor import AudioVideoExtractor
from vocal_music_extractor import VocalMusicExtractor
from background_remover import BackgroundRemover
from splitter import Splitter
from frame_prcessor import FrameProcessor
from video_creater import VideoCreator
import threading
import time
import multiprocessing
from datetime import datetime
import json
from FastBackgroundRemoverCPU import FastBackgroundRemoverCPU
from media_mixer import MediaMixer

def download_video_from_url(video_url,inputput_video_folder):
    print("downloading video Started")
    mediaDownLoader=MediaDownLoader()
    downloaded_video_file=mediaDownLoader.download_video_with_ytdlp(inputput_video_folder,video_url)
    print("downloading video Completed")
    return downloaded_video_file

def audio_video_extract(input_file,input_audio_folder):
    print("Extract video and autio Started")
    mediaExtractor=AudioVideoExtractor()
    video_only_file=mediaExtractor.extract_video(input_file,input_file.replace(".mp4","_video_only.mp4"))
    
    os.makedirs(input_audio_folder, exist_ok=True)
    video_filename=os.path.basename(input_file)
    audio_output_filename=f"{input_audio_folder}/{video_filename}"
    audio_output_filename=audio_output_filename.replace(".mp4",".mp3")
    audio_output_filename=mediaExtractor.extract_audio(input_file,audio_output_filename)
    print("Extract video and autio Completed")
    return (video_only_file,audio_output_filename)

def get_background_removed_video(input_video_file):
    backgroundRemover=BackgroundRemover()
    bgr_output_video=backgroundRemover.remove_video_bg(input_video_file)
    return bgr_output_video

def create_or_update_data(filename,new_data):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = {} # or [] depending on your expected structure
    else:
        existing_data = {} # or [] if you expect a list at the top level

    if isinstance(existing_data, dict):
        existing_data.update(new_data)
    elif isinstance(existing_data, list):
        existing_data.append(new_data)
    else:
        print(f"Warning: Unexpected JSON structure in {filename}. Overwriting.")
        existing_data = new_data
    with open(filename, 'w') as f:
        json.dump(existing_data, f, indent=4) # indent for pretty printing

def instrumental_music_extact(audio_input_filename):
    audio_separator_model="UVR-MDX-NET-Inst_HQ_1"
    vocalMusicExtractor=VocalMusicExtractor(audio_separator_model)
    (instrumental_file,vocals_file)=vocalMusicExtractor.extract_vocal_music(audio_input_filename,audios_folder)
    return (instrumental_file,vocals_file)

def create_video_chunks(input_video_file):
    splitter=Splitter()
    split_duration=15
    root, extension = os.path.splitext(input_video_file)
    output_chunks_folder=root
    video_chunks_folder=splitter.split_video_subprocess(input_video_file, output_chunks_folder, split_duration)
    return video_chunks_folder

def mix_bg_and_audio(foreground_video_path,background_image_path,audio_file_path,output_path):
    mediaMixer=MediaMixer()
    mediaMixer.set_background_image_to_mp4(foreground_video_path,background_image_path,audio_file_path,output_path)
    return output_path

def check_node_existed(json,key):
    return (key in json)
def get_data_from_json(data_filename,key):
    with open(data_filename, 'r') as file:
        jdata = json.load(file)
    return jdata[key]

if __name__=="__main__":
    vidoes_folder = "videos_processing/inputs/videos"
    audios_folder="videos_processing/inputs/audios"
    data_folder="videos_processing/inputs/data"
    print("started")
    os.makedirs(data_folder, exist_ok=True)
    
    # Download mp4
    video_url="https://www.youtube.com/shorts/dul7XqYUf7M"

    data={"video_url":video_url }
    last_part = os.path.basename(video_url)   
    data_filename=f"{data_folder}/{last_part}.json"
    jdata=None
    if not os.path.exists(data_filename):
        create_or_update_data(data_filename,data)
        
    with open(data_filename, 'r') as file:
        jdata = json.load(file)

    if not check_node_existed(jdata,"video_url"):
        data={"video_url":video_url }
        create_or_update_data(data_filename,data)

    if not check_node_existed(jdata,"downloaded_video_file"):
        downloaded_video_file=download_video_from_url(video_url,vidoes_folder)
        data={"downloaded_video_file":downloaded_video_file }
        create_or_update_data(data_filename,data)

    if not check_node_existed(jdata,"video_only_file"):
        downloaded_video_file=get_data_from_json(data_filename,"downloaded_video_file")
        (video_only_file,audio_output_filename)=audio_video_extract(downloaded_video_file,audios_folder)
        data={"video_only_file":video_only_file }
        create_or_update_data(data_filename,data)
    if not check_node_existed(jdata,"audio_output_filename"):
        data={"audio_output_filename":audio_output_filename }
        create_or_update_data(data_filename,data)

    if not check_node_existed(jdata,"instrumental_file") and not check_node_existed(jdata,"vocals_file") :
        print("Vocal and Music Separation Started")
        audio_output_filename=get_data_from_json(data_filename,"audio_output_filename")
        (instrumental_file,vocals_file)=instrumental_music_extact(audio_output_filename)
        print(f"vocal and music separeted extracted")
        data={"instrumental_file":instrumental_file }
        create_or_update_data(data_filename,data)

        data={"vocals_file":vocals_file }
        create_or_update_data(data_filename,data)

    # video_chunks_folder=create_video_chunks(downloaded_video_file)
    # print(f"Video chunks created at {video_chunks_folder}")

    if not check_node_existed(jdata,"bgr_video_created"):
        print("Removing video background started")
        fastBackgroundRemoverCPU=FastBackgroundRemoverCPU()
        downloaded_video_file=get_data_from_json(data_filename,"downloaded_video_file")
        bgr_video_file=fastBackgroundRemoverCPU.remove_video_bg(downloaded_video_file)
        print("Removing video background completed")
        data={"bgr_video_created":bgr_video_file }
        create_or_update_data(data_filename,data)

    if not check_node_existed(jdata,f"finale_video_{last_part}"):
        bgr_video_file=get_data_from_json(data_filename,"bgr_video_created")
        audio_output_filename=get_data_from_json(data_filename,"audio_output_filename")
        foreground_video_path = bgr_video_file
        background_image_path = "videos_processing/background_theme_videos/bg_yellow_red.PNG"         # new background image
        final_video_output_path = f"videos_processing/inputs/videos/final_{last_part}.mp4"
        final_video_output_path=mix_bg_and_audio(foreground_video_path,background_image_path,audio_output_filename,final_video_output_path)
        data={f"finale_video_{last_part}":final_video_output_path }
        create_or_update_data(data_filename,data)


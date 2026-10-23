import os
import sys
import glob
import re
import threading
import subprocess
from pathlib import Path
import numpy as np
from moviepy import VideoFileClip

# =====================================================================
# PART 1: AUDIO/VIDEO CONVERTER & EXTRACTOR CORE
# =====================================================================
class Converter:
    def convert_to_mp4(self, input_file, output_file):
        """Converts media files to MP4 containers securely using FFmpeg."""
        command = [
            'ffmpeg', '-y', # Overwrite output files without asking
            '-i', input_file,
            '-c:v', 'libx264',   
            '-crf', '23',        
            '-preset', 'medium', 
            '-c:a', 'aac',       
            '-b:a', '128k',      
            output_file
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"✅ Successfully converted '{input_file}' to '{output_file}'")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error during conversion: {e}")
            print(f"STDERR: {e.stderr}")
            if os.path.exists(input_file):
                os.remove(input_file)
        except FileNotFoundError:
            print("❌ FFmpeg not found. Please ensure FFmpeg is installed and accessible in your system's PATH.")
        
        if os.path.exists(input_file) and input_file != output_file:
            os.remove(input_file)
        return output_file


class AudioVideoExtractor:
    def extract_video(self, input_video_file_path, output_video_filename):
        """Extracts the video stream completely stripped of its audio track."""
        video_clip = VideoFileClip(input_video_file_path)
        video_only_clip = video_clip.without_audio()
        video_only_clip.write_videofile(output_video_filename, codec='libx264')
        video_only_clip.close()
        video_clip.close()
        print(f"🎥 Video-only file created: {output_video_filename}")
        return output_video_filename
    
    def extract_audio(self, input_video_filepath, output_audio_filename):
        """Extracts the native audio stream from a video container into an MP3."""
        if os.path.exists(input_video_filepath):
            video_clip = VideoFileClip(input_video_filepath)
            audio_clip = video_clip.audio
            audio_clip.write_audiofile(output_audio_filename, codec='mp3')
            audio_clip.close()
            video_clip.close()
            print(f"🎵 Audio extracted to: {output_audio_filename}")
        else:
            print(f"❌ Input file {input_video_filepath} not found.")
        return output_audio_filename


# =====================================================================
# PART 2: OPTIMIZED MEDIA DOWNLOADER 
# =====================================================================
class MediaDownloader:
    def download_video_with_ytdlp(self, output_path, url, file_name_part="", duration=58, extract_audio_only=False):
        """
        Downloads media tracks using yt-dlp via subprocess.
        Handles direct stream-trimming constraints and routes container formats contextually.
        """
        os.makedirs(output_path, exist_ok=True)
        
        # Adjust base extensions dynamically according to asset intent
        ext_target = "mp3" if extract_audio_only else "mp4"
        
        if file_name_part != "":
            out_template = os.path.join(output_path, f"{file_name_part}.%(ext)s")
            final_expected_path = os.path.join(output_path, f"{file_name_part}.{ext_target}")
        else:
            last_part = url.rstrip("/").split("/")[-1]
            out_template = os.path.join(output_path, f"{last_part}_%(title)s.%(ext)s")
            final_expected_path = None

        # Build execution array safely context-switching between full MP4s or Audio-Only tracks
        if extract_audio_only:
            command = [
                'yt-dlp',
                '-o', out_template,
                '-f', 'ba',                   # Fetch best audio stream
                '-x',                         # Extract audio track
                '--audio-format', 'mp3',      # Enforce MP3 transcode binding
                url
            ]
        else:
            command = [
                'yt-dlp',
                '-o', out_template,
                '--merge-output-format', 'mp4',
                '--download-sections', f'*00:00:00-00:00:{duration:02d}',
                '--force-keyframes-at-cuts',
                url
            ]
        
        try:
            # Execute downloader pipeline securely
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"✅ Download process complete for URL: {url}")
            
            if final_expected_path and os.path.exists(final_expected_path):
                return final_expected_path
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error during download processing for {url}: {e}")
            print("yt-dlp stderr details:", e.stderr)
            return None
        except FileNotFoundError:
            print("❌ Error: 'yt-dlp' executable terminal shortcut command not accessible.")
            return None

        # Fallback file discovery scanner structure
        list_of_files = glob.glob(os.path.join(output_path, '*'))
        if not list_of_files:
            return None
            
        latest_file = max(list_of_files, key=os.path.getctime)
        root, ext = os.path.splitext(latest_file)
        
        # Enforce conversions if container mismatches manifest
        if not extract_audio_only and ext.lower() != ".mp4":
            mp4_file_path = f"{root}.mp4"
            converter = Converter() 
            converter.convert_to_mp4(latest_file, mp4_file_path)
            return mp4_file_path
            
        return latest_file


# # =====================================================================
# # PART 3: PIPELINE TEST SUITE ORCHESTRATION
# # =====================================================================
# if __name__ == "__main__":
#     # Test Parameters reflecting your error logs environment setup
#     OUTPUT_AUDIO_DIR = r"C:\Ravi\Python\2025\Media\02_videos_processing\002_QS\outputs\audios"
#     TARGET_URL = "https://www.youtube.com/watch?v=WPni755-Krg"
#     FILE_NAME_BASE = "QS_2027_audio"

#     downloader = MediaDownloader()
    
#     print("🚀 Triggering corrected audio-extracting stream download payload...")
#     downloaded_asset = downloader.download_video_with_ytdlp(
#         output_path=OUTPUT_AUDIO_DIR,
#         url=TARGET_URL,
#         file_name_part=FILE_NAME_BASE,
#         extract_audio_only=True # Resolves the conflict by preventing video packaging constraints
#     )
    
#     print(f"\nFinal processing asset resolved to path location: {downloaded_asset}")
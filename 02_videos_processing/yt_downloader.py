import subprocess
import os
import glob
import threading

class Converter:
    def convert_to_mp4(self, input_file, output_file):
        command = [
            'ffmpeg',
            '-i', input_file,
            '-c:v', 'libx264',   # Video codec for MP4
            '-crf', '23',        # Constant Rate Factor for quality
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
    
    def convert_all_web_to_mp4(self, input_video_folder):
        file_names = sorted(
            f for f in os.listdir(input_video_folder) if f.endswith(".webm")
        )
        for item in file_names:
            input_file_path = os.path.join(input_video_folder, item)
            output_file_path = os.path.join(input_video_folder, item.replace(".webm", ".mp4"))
            self.convert_to_mp4(input_file_path, output_file_path)
        print("Conversion completed")


class MediaDownLoader:
    def download_video_with_ytdlp(self, output_path, url, file_name_part="", duration=58):
        """
        Downloads a video using yt-dlp via subprocess. 
        Trims the video directly from the stream if it exceeds the specified duration constraint.

        Args:
            output_path (str): The directory where the video will be saved.
            url (str): The URL of the video to download.
            file_name_part (str): Optional custom name for the file.
            duration (int): Maximum cut-off duration in seconds. Defaults to 58.
        """
        # Ensure the output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        # FIX 1: Clean tracking strings (e.g., ?igsh=...) from the URL to protect Windows file paths
        clean_url = url.split('?')[0]
        
        # Decide the base output naming convention
        if file_name_part != "":
            out_template = os.path.join(output_path, f"{file_name_part}.%(ext)s")
        else:
            last_part = clean_url.rstrip("/").split("/")[-1]
            out_template = f"{output_path}/{last_part}_%(title)s.%(ext)s"

        # Construct the base yt-dlp command
        command = [
            'tools/yt-dlp',
            '-o', out_template,
            '--merge-output-format', 'mp4', # Forces/merges the final container to be MP4
            # Direct stream trimming configuration via internal ffmpeg arguments
            '--download-sections', f'*00:00:00-00:00:{duration:02d}',
            '--force-keyframes-at-cuts',
            # FIX 2: Instruct yt-dlp to pass cookies from your desktop browser to bypass Instagram's bot block
            '--cookies-from-browser', 'firefox',
            clean_url
        ]
        
        mp4_file_path = None  
        try:
            # Run the download command
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"✅ Download complete for: {clean_url}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error during download for {clean_url}: {e}")
            print("yt-dlp stderr:", e.stderr)
            return None
        except FileNotFoundError:
            print("❌ Error: yt-dlp tool not found at 'tools/yt-dlp'.")
            return None
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")
            return None
        
        # Find the downloaded file
        list_of_files = glob.glob(os.path.join(output_path, '*'))
        if not list_of_files:
            print("❌ No files found in the output directory after download.")
            return None
            
        latest_file = max(list_of_files, key=os.path.getctime)
        print(f"-> Selected file: {latest_file}")
        
        root, ext = os.path.splitext(latest_file)
        
        # If yt-dlp couldn't containerize to mp4 natively, keep your original fallback converter logic
        if ext.lower() != ".mp4":
            mp4_file_path = f"{root}.mp4"
            print(f"🔄 Container mismatch ({ext}). Converting {latest_file} to MP4...")
            try:
                converter = Converter() 
                converter.convert_to_mp4(latest_file, mp4_file_path)
                if os.path.exists(latest_file):
                    os.remove(latest_file)
            except NameError:
                print("⚠️ Converter class is not defined. Returning original file path.")
                return latest_file
        else:
            mp4_file_path = latest_file
            
        return mp4_file_path
    
# to download video from singl youtube instagram url
# if __name__ == "__main__":
#     inputput_video_folder = "inputs/videos"
#     output_dir = "inputs/videos"
#     video_url="https://www.youtube.com/shorts/GmyuZqrDUAM"
#     mediaDownLoader=MediaDownLoader()
#     mediaDownLoader.download_video_with_ytdlp(output_dir,video_url, inputput_video_folder)


# if __name__ == "__main__":
#     inputput_video_folder = "inputs/videos"
#     video_urls_list=["https://www.youtube.com/shorts/Rau7b2bFlCc",
#                     "https://www.youtube.com/shorts/FX4S7w5wW9U",
#                     "https://www.youtube.com/shorts/n5a3P5BMH1U",
#                     "https://www.youtube.com/shorts/GmyuZqrDUAM"
#                  ]

#     mediaDownLoader=MediaDownLoader()
#     threads = []
#     output_path="inputs/videos"
#     for item in video_urls_list:
#         t = threading.Thread(target=mediaDownLoader.download_video_with_ytdlp, args=(output_path,item,))
#         threads.append(t)
#         t.start()

#     # block until all the threads finish (i.e. until all function_a functions finish)    
#     for t in threads:
#         t.join()
#     print("downloaded complted")
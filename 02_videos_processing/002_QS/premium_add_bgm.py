from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
from moviepy.audio.fx import MultiplyVolume  # Modern FX import
from pathlib import Path
import os

class BgmAudioAdder:
    # 1. FIXED: Changed 'vself' to 'self'
    def add_bgm_inplace(self, video_path, bgm_path, bgm_volume=0.09):
        """
        Adds background music to a video file and overwrites the original video file.
        """
        video_clip_path = Path(video_path)
        
        # Define a temporary file path in the same directory
        temp_output_path = video_clip_path.with_name(f"temp_{video_clip_path.name}")
        
        # 1. Load video and background music
        video = VideoFileClip(str(video_clip_path))
        bgm = AudioFileClip(str(bgm_path))
        
        # 2. Adjust BGM duration (Trim or Loop)
        if bgm.duration > video.duration:
            bgm = bgm.subclipped(0, video.duration)
        elif bgm.duration < video.duration:
            audio_segments = []
            current_time = 0
            while current_time < video.duration:
                if current_time + bgm.duration > video.duration:
                    segment = bgm.subclipped(0, video.duration - current_time)
                else:
                    segment = bgm
                audio_segments.append(segment.with_start(current_time))
                current_time += bgm.duration
            bgm = CompositeAudioClip(audio_segments)

        # 2. FIXED: Replaced legacy .fx() with modern MoviePy v2 .with_effects()
        bgm = bgm.with_effects([MultiplyVolume(bgm_volume)])

        # 3. Layer audio tracks
        if video.audio is not None:
            final_audio = CompositeAudioClip([video.audio, bgm])
        else:
            final_audio = bgm

        # 4. Export to the temporary file
        final_video = video.with_audio(final_audio)
        
        print(f"Processing audio for: {video_clip_path.name}...")
        final_video.write_videofile(
            str(temp_output_path), 
            codec="libx264", 
            audio_codec="aac"
        )
        
        # 5. MUST close clips to release the file locks before replacing
        video.close()
        bgm.close()
        final_video.close()
        
        # 6. Overwrite the original file with the temporary one safely
        try:
            temp_output_path.replace(video_clip_path)
            print(f"Successfully updated original file in-place: {video_clip_path.resolve()}")
        except Exception as e:
            print(f"Error replacing original file: {e}")
            print(f"Your processed video is saved as: {temp_output_path}")

# if __name__ == "__main__":
#     bgmAudioAdder = BgmAudioAdder()
#     BASE_DIR = Path(__file__).resolve().parent
    
#     input_video = BASE_DIR / "outputs" / "videos" / "NIRF_pharmacy_2025_Ranking.mp4"
    
#     # 3. FIXED: Swapped out '.mp4' extension for '.mp3' for the background track
#     background_audio = BASE_DIR / "outputs" / "audios" / "NIRF_pharmacy_2025_Ranking.mp4"
    
#     bgmAudioAdder.add_bgm_inplace(input_video, background_audio)
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip,AudioFileClip
class MediaMixer:
    def set_background_image_to_mp4(self,foreground_video_path,background_image_path,audio_file_path,output_path ):
        fg = VideoFileClip(foreground_video_path).with_opacity(0.7)
        fg = fg.resized(0.9).with_position("center")
        bg = (
            ImageClip(background_image_path)
            .resized(fg.size)
            .with_duration(fg.duration)
            .with_opacity(1.0)
        )
        final = CompositeVideoClip([bg, fg])
        audio = AudioFileClip(audio_file_path)
        final = final.with_audio(audio)
        final.write_videofile(output_path, fps=fg.fps, codec="libx264", audio_codec="aac")

# foreground_video_path = "inputs/videos/Meesaala Pilla Song_bgr.mp4"   # your background-removed MP4
# background_image_path = "background_theme_videos/green_bg.jpeg"         # new background image
# output_path = "inputs/videos/final_video_output.mp4"
# audio_file_path="inputs/audios/Meesaala.mp3"
# mediaMixer=MediaMixer()
# mediaMixer.set_background_image_to_mp4(foreground_video_path,background_image_path,audio_file_path,output_path)



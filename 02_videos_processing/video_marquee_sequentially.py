import os
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

# Folder containing videos
folder_path = "videos_processing/outputs/Original Vs Copied Tollywood Songs"

# Get all video files
video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)
               if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi"))]
video_files.sort()

# Load clips
clips = []
for f in video_files:
    clip = VideoFileClip(f)
    clips.append(clip)

# Sequentially place clips by start time
current_time = 0
for clip in clips:
    try:
        clip = clip.set_start(current_time)
    except AttributeError:
        pass
    current_time += getattr(clip, "duration", 5)

# Combine all clips
final_video = CompositeVideoClip(clips)

# Export (audio from first clip only, if supported)
final_video.write_videofile(
    "videos_processing/outputs/legacy_concat_video.mp4",
    codec="libx264",
    audio=True  # some old versions will ignore this if audio can't be set
)

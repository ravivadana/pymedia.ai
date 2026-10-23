import os
from moviepy import VideoFileClip, concatenate_videoclips


def get_video_files_recursively(folder, extensions=("mp4", "mov", "avi", "mkv")):
    video_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(extensions):
                video_files.append(os.path.join(root, file))
    return sorted(video_files)


def append_videos_from_folder(folder, output_path="output.mp4"):
    video_files = get_video_files_recursively(folder)

    if len(video_files) < 2:
        raise ValueError("Need at least two video files to append.")

    first_clip = VideoFileClip(video_files[0])
    clips = [first_clip]

    for path in video_files[1:]:
        clip = VideoFileClip(path)
        #clip = clip.resized(first_clip.size).set_fps(first_clip.fps)
        clips.append(clip)

    final_clip = concatenate_videoclips(clips, method="compose")

    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac"
    )

    for clip in clips:
        clip.close()
    final_clip.close()


# Example usage
folder_path = f"02_videos_processing/inputs"
append_videos_from_folder(folder_path, "02_videos_processing/gmritsj2026_mobile.mp4")

import subprocess
from pathlib import Path
import os
import re

project_folder="videos_processing"
input_file = f"{project_folder}/inputs/videos/Original Vs Copied Tollywood Songs.mp4"
filename_without_extension = Path(input_file).stem
output_folder=f"{project_folder}/outputs/{filename_without_extension}"
os.makedirs(output_folder, exist_ok=True)

cmd = [
    "ffmpeg",
    "-i", input_file,
    "-af", "silencedetect=n=-30dB:d=0.5",
    "-f", "null",
    "-"
]

process = subprocess.run(
    cmd,
    stderr=subprocess.PIPE,
    text=True
)

silences = []
for line in process.stderr.splitlines():
    if "silence_start" in line:
        silences.append(float(re.search(r"silence_start: ([0-9.]+)", line).group(1)))


video_duration = 257  # seconds (or get via ffprobe)

segments = []
start = 0
MIN_CLIP_DURATION = 1.0  # seconds
prev_end = 0.0

for silence_start in silences:
    if silence_start > prev_end:
        duration = silence_start - prev_end
        if duration >= MIN_CLIP_DURATION:
            segments.append((prev_end, silence_start))
        prev_end = silence_start

# Add last segment safely
if video_duration > prev_end:
    duration = video_duration - prev_end
    if duration >= MIN_CLIP_DURATION:
        segments.append((prev_end, video_duration))

for i, (start, end) in enumerate(segments, 1):
    duration = end - start
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-ss", str(start),
        "-t", str(duration),
        f"{output_folder}/{i}.mp4"
    ]

    subprocess.run(cmd, check=True)
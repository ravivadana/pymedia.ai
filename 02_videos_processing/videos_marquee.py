import cv2
import numpy as np
import os
import subprocess
from pathlib import Path
from collections import Counter


class VideosMarquee:

    def apply_marquee_shift(self, stacked, offset, direction, w, h):
        if direction == "up":
            M = np.float32([[1, 0, 0], [0, 1, -offset]])
            shifted = cv2.warpAffine(
                stacked, M, (w, stacked.shape[0]),
                borderMode=cv2.BORDER_WRAP
            )
            return shifted[:h, :w]

        elif direction == "down":
            M = np.float32([[1, 0, 0], [0, 1, offset]])
            shifted = cv2.warpAffine(
                stacked, M, (w, stacked.shape[0]),
                borderMode=cv2.BORDER_WRAP
            )
            return shifted[:h, :w]

        elif direction == "left":
            M = np.float32([[1, 0, -offset], [0, 1, 0]])
            shifted = cv2.warpAffine(
                stacked, M, (stacked.shape[1], stacked.shape[0]),
                borderMode=cv2.BORDER_WRAP
            )
            return shifted[:h, :w]

        elif direction == "right":
            M = np.float32([[1, 0, offset], [0, 1, 0]])
            shifted = cv2.warpAffine(
                stacked, M, (stacked.shape[1], stacked.shape[0]),
                borderMode=cv2.BORDER_WRAP
            )
            return shifted[:h, :w]

        elif direction == "diagonal":
            M = np.float32([[1, 0, offset], [0, 1, offset]])
            shifted = cv2.warpAffine(
                stacked, M, (stacked.shape[1], stacked.shape[0]),
                borderMode=cv2.BORDER_WRAP
            )
            return shifted[:h, :w]

        else:
            raise ValueError("Invalid direction")

    def create_marquee_video(self, input_dir, output_dir, direction):
        extensions = (".mp4", ".mov", ".avi", ".webm")
        target_width = 720  # optional for scaling, not used with exact size
        os.makedirs(output_dir, exist_ok=True)

        video_files = [
            os.path.join(input_dir, f)
            for f in os.listdir(input_dir)
            if f.lower().endswith(extensions)
        ]

        if len(video_files) < 2:
            raise RuntimeError("Need at least 2 videos in the folder")

        # ---------------- Sort by duration ----------------
        durations = []
        for vf in video_files:
            cap = cv2.VideoCapture(vf)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            durations.append((vf, frames / fps))
            cap.release()

        video_files = [v for v, _ in sorted(durations, key=lambda x: x[1], reverse=True)]

        # ---------------- Collect video sizes ----------------
        size_counter = Counter()
        video_sizes = {}

        for vf in video_files:
            cap = cv2.VideoCapture(vf)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                continue
            h, w, _ = frame.shape
            video_sizes[vf] = (w, h)
            size_counter[(w, h)] += 1

        if not size_counter:
            raise RuntimeError("No valid video frames found")

        # ---------------- Most common size ----------------
        ref_size, _ = size_counter.most_common(1)[0]
        ref_w, ref_h = ref_size
        print(f"Using most common size: {ref_w}x{ref_h}")

        # ---------------- Filter videos ----------------
        uniform_videos = []
        skipped_videos = []

        for vf, size in video_sizes.items():
            if size == ref_size:
                uniform_videos.append(vf)
            else:
                skipped_videos.append(vf)

        video_files = uniform_videos

        if skipped_videos:
            print("Skipped clips (non-matching size):")
            for vf in skipped_videos:
                print(f"  {vf}")

        if len(video_files) < 2:
            raise RuntimeError("Need at least 2 videos with identical size for marquee")

        first_video = video_files[0]
        filename = Path(first_video).name
        temp_video = f"{output_dir}/temp_{filename}"
        final_video = f"{output_dir}/final_{filename}"

        # ---------------- First video info ----------------
        cap = cv2.VideoCapture(first_video)
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = frame_count / fps

        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("Cannot read first frame")

        h, w, _ = frame.shape
        fade_height = max(10, h // 10)

        # ---------------- Open captures ----------------
        caps = [cv2.VideoCapture(v) for v in video_files]

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(temp_video, fourcc, fps, (w, h))

        def cross_fade(a, b, fh):
            alpha = np.linspace(0, 1, fh)[:, None, None]
            return ((1 - alpha) * a[-fh:] + alpha * b[:fh]).astype(np.uint8)

        # ---------------- Preload frames ----------------
        frame_buffer = []
        for cap in caps:
            ret, f = cap.read()
            if not ret:
                raise RuntimeError("Frame read error")
            frame_buffer.append(f)  # exact size guaranteed

        # ---------------- Scroll setup ----------------
        strip_height = len(frame_buffer) * (h - fade_height) + fade_height * (len(frame_buffer) - 1)
        total_frames = int(fps * duration_sec)
        speed = strip_height / total_frames
        offset = 0.0

        # ---------------- Generate marquee ----------------
        for _ in range(total_frames):
            tall_strip = []

            for i in range(len(frame_buffer) - 1):
                A = frame_buffer[i]
                B = frame_buffer[i + 1]
                tall_strip.append(A[:-fade_height])
                tall_strip.append(cross_fade(A, B, fade_height))

            tall_strip.append(frame_buffer[-1][:-fade_height])
            stacked = np.vstack(tall_strip)

            out_frame = self.apply_marquee_shift(
                stacked, offset, direction, w, h
            )
            out.write(out_frame)

            offset = (offset + speed) % stacked.shape[0]

            # update frames
            for i, cap in enumerate(caps):
                ret, f = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, f = cap.read()
                frame_buffer[i] = f  # exact size

        out.release()
        for cap in caps:
            cap.release()

        # ---------------- Attach audio ----------------
        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", first_video,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            final_video
        ], check=True)

        os.remove(temp_video)
        return final_video

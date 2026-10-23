import os
import subprocess
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

MP4_DIR = "04_audio_processing/inputs/videos"
OUTPUT_DIR = "04_audio_processing/outputs/audios"
BITRATE = "128k"

os.makedirs(OUTPUT_DIR, exist_ok=True)

seen_hashes = set()
hash_lock = Lock()

def extract_wav(mp4_path, wav_path):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", mp4_path,
            "-vn",
            "-ac", "1",        # mono
            "-ar", "16000",    # normalize sample rate
            "-acodec", "pcm_s16le",
            wav_path
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def wav_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def wav_to_mp3(wav_path, mp3_path):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", wav_path,
            "-ab", BITRATE,
            "-acodec", "libmp3lame",
            mp3_path
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def process_file(filename):
    if not filename.lower().endswith(".mp4"):
        return

    mp4_path = os.path.join(MP4_DIR, filename)
    base = os.path.splitext(filename)[0]

    temp_wav = f"temp_{uuid.uuid4().hex}.wav"
    extract_wav(mp4_path, temp_wav)

    if not os.path.exists(temp_wav):
        return

    audio_hash = wav_hash(temp_wav)

    with hash_lock:
        if audio_hash in seen_hashes:
            os.remove(temp_wav)
            return
        seen_hashes.add(audio_hash)

    final_mp3 = os.path.join(OUTPUT_DIR, f"{base}.mp3")
    wav_to_mp3(temp_wav, final_mp3)
    os.remove(temp_wav)

    print(f"Saved distinct audio: {final_mp3}")

def main():
    files = os.listdir(MP4_DIR)
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        executor.map(process_file, files)

    print(f"\nSaved {len(seen_hashes)} distinct MP3 files")

if __name__ == "__main__":
    main()

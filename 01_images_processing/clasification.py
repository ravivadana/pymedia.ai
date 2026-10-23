import os
import shutil
from datetime import datetime
from PIL import Image, ExifTags
from pymediainfo import MediaInfo

# Configuration
SOURCE_DIR = r"C:\Users\ravik\Desktop\House Warming"
OUTPUT_DIR = r"C:\Users\ravik\Desktop\House Warming\output"

# Output folder names
DEST_FOLDERS = {
    "img_portrait": os.path.join(OUTPUT_DIR, "1_images_portrait"),
    "img_landscape": os.path.join(OUTPUT_DIR, "2_images_landscape"),
    "vid_portrait": os.path.join(OUTPUT_DIR, "3_videos_portrait"),
    "vid_landscape": os.path.join(OUTPUT_DIR, "4_videos_landscape"),
}

# Extensions to scan
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".tiff", ".webp", ".cr2", ".nef"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".wmv"}


def get_image_metadata(file_path):
    """Extract capture timestamp and orientation/aspect ratio for images."""
    creation_time = None
    width, height = None, None
    orientation = 1

    try:
        with Image.open(file_path) as img:
            width, height = img.size
            exif = img._getexif()

            if exif:
                # Find EXIF tag keys
                exif_data = {
                    ExifTags.TAGS.get(k, k): v
                    for k, v in exif.items()
                    if k in ExifTags.TAGS
                }

                # Get capture date/time
                date_str = exif_data.get("DateTimeOriginal") or exif_data.get("DateTime")
                if date_str:
                    try:
                        creation_time = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass

                # EXIF Orientation Tag (3, 6, 8 swap or rotate image)
                orientation = exif_data.get("Orientation", 1)

    except Exception as e:
        print(f"Warning reading EXIF for {file_path}: {e}")

    # Fallback to file modification time if EXIF timestamp missing
    if not creation_time:
        creation_time = datetime.fromtimestamp(os.path.getmtime(file_path))

    # Adjust dimensions based on EXIF rotation flags
    # Orientations 5, 6, 7, 8 swap width and height
    if orientation in (5, 6, 7, 8) and width and height:
        width, height = height, width

    is_portrait = (height > width) if (width and height) else False
    return creation_time, is_portrait


def get_video_metadata(file_path):
    """Extract capture timestamp and orientation for videos using MediaInfo."""
    creation_time = None
    is_portrait = False

    try:
        media_info = MediaInfo.parse(file_path)
        for track in media_info.tracks:
            if track.track_type == "Video":
                width = int(track.width) if track.width else None
                height = int(track.height) if track.height else None
                rotation = float(track.rotation) if track.rotation else 0.0

                # Swap width/height if video has 90 or 270 degree rotation metadata
                if int(rotation) in (90, 270) and width and height:
                    width, height = height, width

                if width and height:
                    is_portrait = height > width

            if track.track_type in ("General", "Video") and not creation_time:
                # MediaInfo records tagged_date or encoded_date
                date_str = track.tagged_date or track.encoded_date
                if date_str:
                    # Clean up timezone suffix if present (e.g., UTC 2023-05-10 12:00:00)
                    clean_str = date_str.replace("UTC ", "").strip()
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Z %Y-%m-%d %H:%M:%S"):
                        try:
                            creation_time = datetime.strptime(clean_str[:19], "%Y-%m-%d %H:%M:%S")
                            break
                        except ValueError:
                            pass

    except Exception as e:
        print(f"Warning reading Video metadata for {file_path}: {e}")

    if not creation_time:
        creation_time = datetime.fromtimestamp(os.path.getmtime(file_path))

    return creation_time, is_portrait


def process_media():
    # Create target directories
    for folder in DEST_FOLDERS.values():
        os.makedirs(folder, exist_ok=True)

    collected_files = []

    print("Scanning directory recursively...")
    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            file_path = os.path.join(root, file)

            if ext in IMAGE_EXTS:
                creation_time, is_portrait = get_image_metadata(file_path)
                category = "img_portrait" if is_portrait else "img_landscape"
                collected_files.append((file_path, creation_time, category))

            elif ext in VIDEO_EXTS:
                creation_time, is_portrait = get_video_metadata(file_path)
                category = "vid_portrait" if is_portrait else "vid_landscape"
                collected_files.append((file_path, creation_time, category))

    # Sort files by creation metadata chronologically
    collected_files.sort(key=lambda x: x[1])

    print(f"Found {len(collected_files)} media files. Copying sorted files...")

    # Organize into destination folders with chronological index prefix
    for idx, (src_path, cap_time, category) in enumerate(collected_files, start=1):
        dest_folder = DEST_FOLDERS[category]
        filename = os.path.basename(src_path)

        # Prefix filename with 4-digit index to maintain strict sort order in filesystem
        new_filename = f"{idx:04d}_{filename}"
        dest_path = os.path.join(dest_folder, new_filename)

        # Use shutil.copy2 to preserve file creation/modification timestamps
        shutil.copy2(src_path, dest_path)
        print(f"[{idx}/{len(collected_files)}] [{cap_time}] -> {category}/{new_filename}")

    print("/nSorting complete!")


if __name__ == "__main__":
    process_media()
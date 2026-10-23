import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from PIL import Image
import imagehash
import cv2

# --- CONFIGURATION ---
ZIP_FOLDER = r"c:\Users\ravik\Downloads"        # Folder containing your .zip archives
OUTPUT_DIR = r"c:\Users\ravik\Downloads\cleaned_photos"   # Where unique & best photos are saved
DUPLICATE_DIR = r"c:\Users\ravik\Downloads\duplicates"     # Where lower-quality duplicates go

# Distance threshold (0 = exact match, 1-5 = compressed/resized duplicates)
HASH_THRESHOLD = 4
VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff")


def extract_zips_safely(source_folder, target_extract_dir):
    """
    Extracts all .zip files in source_folder (and nested zips) 
    without copying non-zip files or looping endlessly.
    """
    # Find all initial .zip files in source_folder
    zip_queue = []
    for root, dirs, files in os.walk(source_folder):
        # Ignore our own output directories if they exist inside source
        if os.path.abspath(root).startswith(os.path.abspath(OUTPUT_DIR)) or \
           os.path.abspath(root).startswith(os.path.abspath(DUPLICATE_DIR)):
            continue
        for file in files:
            if file.lower().endswith(".zip"):
                zip_queue.append(os.path.join(root, file))

    print(f"Found {len(zip_queue)} root .zip files to extract...")

    extracted_count = 0
    # Process zip queue (and add nested zips as they are discovered)
    while zip_queue:
        current_zip = zip_queue.pop(0)
        target_subfolder = os.path.join(target_extract_dir, f"zip_{extracted_count}")
        extracted_count += 1

        try:
            with zipfile.ZipFile(current_zip, 'r') as zip_ref:
                zip_ref.extractall(target_subfolder)

            # Check if extracting this zip revealed nested .zip files
            for root, _, files in os.walk(target_subfolder):
                for file in files:
                    if file.lower().endswith(".zip"):
                        nested_path = os.path.join(root, file)
                        zip_queue.append(nested_path)

        except (zipfile.BadZipFile, PermissionError) as e:
            print(f"Skipping unreadable/corrupt zip: {current_zip} ({e})")


def collect_images_recursively(base_dir):
    """Recursively scans base_dir and returns paths to all valid image files."""
    image_paths = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith(VALID_EXTENSIONS):
                image_paths.append(os.path.join(root, file))
    return image_paths


def calculate_image_score(image_path):
    """Scores image quality using Resolution, Sharpness (OpenCV Laplacian), and File Size."""
    try:
        file_size = os.path.getsize(image_path)
        
        with Image.open(image_path) as img:
            width, height = img.size
            megapixels = (width * height) / 1e6

        cv_img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        sharpness = cv2.Laplacian(cv_img, cv2.CV_64F).var() if cv_img is not None else 0

        return (megapixels * 100) + (sharpness * 2) + (file_size / 1024 / 1024)
    except Exception as e:
        print(f"Error reading image quality for {image_path}: {e}")
        return 0


def group_similar_images(image_paths, threshold=HASH_THRESHOLD):
    """Groups visually near-identical images using Difference Hash (dhash)."""
    hashes = {}
    print("Hashing images for comparison...")
    for path in image_paths:
        try:
            with Image.open(path) as img:
                hashes[path] = imagehash.dhash(img)
        except Exception as e:
            print(f"Skipping unreadable image {path}: {e}")

    visited = set()
    groups = []
    paths = list(hashes.keys())

    print("Comparing images and finding duplicates...")
    for i, path1 in enumerate(paths):
        if path1 in visited:
            continue

        current_group = [path1]
        visited.add(path1)

        for path2 in paths[i + 1:]:
            if path2 in visited:
                continue

            if hashes[path1] - hashes[path2] <= threshold:
                current_group.append(path2)
                visited.add(path2)

        groups.append(current_group)

    return groups


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DUPLICATE_DIR, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_extract_dir:
        # Extract zips safely without copying non-zip files from Downloads
        extract_zips_safely(ZIP_FOLDER, temp_extract_dir)

        # Collect images
        all_images = collect_images_recursively(temp_extract_dir)
        print(f"Total extracted images found across all zip files: {len(all_images)}")

        if not all_images:
            print("No images were found in the zip archives.")
            return

        groups = group_similar_images(all_images)

        kept_count = 0
        duplicate_count = 0

        for group in groups:
            if len(group) == 1:
                src = group[0]
                filename = f"{kept_count + 1}_{os.path.basename(src)}"
                shutil.copy(src, os.path.join(OUTPUT_DIR, filename))
                kept_count += 1
            else:
                scored_images = [(path, calculate_image_score(path)) for path in group]
                scored_images.sort(key=lambda x: x[1], reverse=True)

                best_image = scored_images[0][0]
                best_filename = f"best_{kept_count + 1}_{os.path.basename(best_image)}"
                shutil.copy(best_image, os.path.join(OUTPUT_DIR, best_filename))
                kept_count += 1

                for dup_path, _ in scored_images[1:]:
                    dup_filename = f"dup_{duplicate_count + 1}_{os.path.basename(dup_path)}"
                    shutil.copy(dup_path, os.path.join(DUPLICATE_DIR, dup_filename))
                    duplicate_count += 1

    print("\n--- Summary ---")
    print(f"Unique/Best photos saved to '{OUTPUT_DIR}': {kept_count}")
    print(f"Discarded duplicates saved to '{DUPLICATE_DIR}': {duplicate_count}")


if __name__ == "__main__":
    main()
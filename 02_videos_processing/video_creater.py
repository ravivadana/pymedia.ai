from moviepy import ImageSequenceClip
from PIL import Image, ImageFile
import os

class VideoCreator:
    # Allow PIL to load truncated images (common fix)
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    def create_mp4_from_png(self, input_folder, output_video_file):
        try:
            fps = 48
            image_files = sorted([
                os.path.join(input_folder, img)
                for img in os.listdir(input_folder)
                if img.lower().endswith(".png")
            ])

            valid_images = []

            # Validate & repair images
            for img_path in image_files:
                try:
                    with Image.open(img_path) as im:
                        im.verify()  # check integrity
                    valid_images.append(img_path)
                except Exception as e:
                    print(f"⚠️ Skipping corrupted image: {img_path} ({e})")

            if not valid_images:
                print("No valid PNG images found. Cannot create video.")
                return

            clip = ImageSequenceClip(valid_images, fps=fps)
            clip.write_videofile(output_video_file, codec='libx264')

        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        finally:
            print("Execution complete.")

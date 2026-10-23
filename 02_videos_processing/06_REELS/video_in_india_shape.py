import os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

import geopandas as gpd
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import moviepy.video.fx as vfx


def create_india_mask_image(shapefile_path, output_mask_path="india_mask.png", image_size=(1080, 1920)):
    """
    Renders a black-and-white mask image where the India map shape is white
    and the background is black.
    """
    print("Loading and processing India shapefile...")
    raw_data = gpd.read_file(shapefile_path)

    # Base boundary
    india_base = raw_data[
        (raw_data.geometry.notnull()) & 
        ((raw_data['admin'] == 'India') | (raw_data['admin'] == 'India/Pakistan boundary'))
    ].copy()

    # Disputed regions
    disputed_regions = raw_data[
        raw_data['name'].isin(['Azad Kashmir', 'Gilgit-Baltistan', 'Aksai Chin', 'Jammu and Kashmir', 'Ladakh']) |
        raw_data['admin'].str.contains('Jammu & Kashmir', case=False, na=False)
    ].copy()

    for idx, row in disputed_regions.iterrows():
        name_str = str(row['name'])
        if name_str in ['Azad Kashmir', 'Gilgit-Baltistan', 'Jammu and Kashmir']:
            disputed_regions.at[idx, 'name'] = 'Jammu and Kashmir'
        elif name_str in ['Aksai Chin', 'Ladakh']:
            disputed_regions.at[idx, 'name'] = 'Ladakh'
        disputed_regions.at[idx, 'admin'] = 'India'

    combined_gdf = gpd.GeoDataFrame(
        gpd.pd.concat([india_base, disputed_regions], ignore_index=True), 
        crs=raw_data.crs
    )
    india_states = combined_gdf.dissolve(by='admin', as_index=False)
    india_states = india_states.to_crs(epsg=3857)

    # Render white shape on black background
    fig, ax = plt.subplots(figsize=(image_size[0] / 100, image_size[1] / 100), dpi=100)
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # Plot India map as solid white
    india_states.plot(ax=ax, facecolor='white', edgecolor='white', linewidth=1)

    bounds = india_states.total_bounds
    
    # Adjust canvas bounds tight to India
    ax.set_xlim(bounds[0] - 100000, bounds[2] + 100000)
    ax.set_ylim(bounds[1] - 100000, bounds[3] + 100000)

    plt.savefig(output_mask_path, facecolor='black', edgecolor='none', pad_inches=0)
    plt.close(fig)
    print(f"Mask created at: {output_mask_path}")


def crop_to_fill(clip, target_size=(1080, 1920)):
    """
    Zooms and center-crops the video clip to completely fill the target dimensions.
    """
    target_w, target_h = target_size
    clip_w, clip_h = clip.size

    # Calculate scale factor to cover the target dimensions completely
    scale = max(target_w / clip_w, target_h / clip_h)
    
    # Resize keeping aspect ratio
    new_w, new_h = int(clip_w * scale), int(clip_h * scale)
    resized_clip = clip.resized((new_w, new_h))

    # Center crop to target size
    x_center = new_w / 2
    y_center = new_h / 2
    
    cropped_clip = resized_clip.cropped(
        x_center=x_center, 
        y_center=y_center, 
        width=target_w, 
        height=target_h
    )
    return cropped_clip


def play_video_in_india_shape(input_video_path, shapefile_path, output_video_path="india_shaped_video.mp4", canvas_size=(1080, 1920)):
    """
    Applies the India map mask to an input video stream with proper zoom-to-fill scaling.
    """
    mask_file = "temp_india_mask.png"
    
    # Step 1: Generate static mask matching the canvas resolution
    create_india_mask_image(shapefile_path, output_mask_path=mask_file, image_size=canvas_size)

    print("Processing video mask overlay...")
    video = VideoFileClip(str(input_video_path))

    # Step 2: Scale and Center-Crop video to fill the 1080x1920 canvas
    filled_video = crop_to_fill(video, target_size=canvas_size)

    # Step 3: Load single-channel mask matching the canvas size
    mask_clip = ImageClip(mask_file, is_mask=True).resized(canvas_size)

    # Step 4: Apply mask to the filled video
    masked_video = filled_video.with_mask(mask_clip)

    # Step 5: Wrap inside CompositeVideoClip
    final_clip = CompositeVideoClip([masked_video], size=canvas_size)

    # Ensure output directory exists before writing
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

    # Write output video
    final_clip.write_videofile(
        str(output_video_path), 
        codec="libx264", 
        audio_codec="aac",
        preset="medium"
    )

    # Cleanup clips
    video.close()
    final_clip.close()

    if os.path.exists(mask_file):
        os.remove(mask_file)

    print(f"✅ Video successfully created: {output_video_path}")


if __name__ == "__main__":
    COMMON_ASSETS = Path("C:/Ravi/Python/2025/Media/assets/common")
    SHAPEFILE_PATH = COMMON_ASSETS / "maps" / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp"
    INPUT_VIDEO_PATH = "C:/Ravi/Python/2025/Media/02_videos_processing/06_REELS/girl_english_song_in_india.mp4"
    OUTPUT_VIDEO_PATH = "C:/Ravi/Python/2025/Media/02_videos_processing/06_REELS/girl_english_song_in_india_output.mp4"

    if os.path.exists(SHAPEFILE_PATH) and os.path.exists(INPUT_VIDEO_PATH):
        play_video_in_india_shape(INPUT_VIDEO_PATH, SHAPEFILE_PATH, OUTPUT_VIDEO_PATH)
    else:
        print("⚠️ Please verify that both SHAPEFILE_PATH and INPUT_VIDEO_PATH exist.")
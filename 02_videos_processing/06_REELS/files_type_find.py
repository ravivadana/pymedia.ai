import json
import os
from moviepy import VideoFileClip, concatenate_audioclips

def create_audio_pipeline(input_folder, audios_output_dir, final_audio_path, output_json_name="media_paths.json", transition_duration=1.0):
    video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm')
    
    media_data = {
        "input_folder": os.path.abspath(input_folder),
        "audios_folder": os.path.abspath(audios_output_dir),
        "individual_audios": [],
        "final_audio": os.path.abspath(final_audio_path)
    }
    
    if not os.path.exists(input_folder):
        print(f"❌ Error: The folder '{input_folder}' does not exist.")
        return

    # Ensure the individual audios directory exists
    os.makedirs(audios_output_dir, exist_ok=True)

    # 1. Gather all video files across nested folders
    for root, dirs, files in os.walk(input_folder):
        for file_name in files:
            full_path = os.path.abspath(os.path.join(root, file_name))
            if file_name.lower().endswith(video_extensions):
                media_data["individual_audios"].append(full_path) # placeholder temporarily, will update with audio paths

    if not media_data["individual_audios"]:
        print("❌ No videos found in the specified folder.")
        return

    print(f"🔍 Found {len(media_data['individual_audios'])} videos. Extracting audio tracks...")

    audio_clips = []
    saved_audio_paths = []
    
    # 2. Extract audio track from each video and save to the audios folder first
    video_paths = media_data["individual_audios"]
    media_data["individual_audios"] = []  # Reset to store individual audio paths

    for i, video_path in enumerate(video_paths):
        try:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            individual_mp3_name = f"{i:03d}_{base_name}.mp3"
            individual_mp3_path = os.path.join(audios_output_dir, individual_mp3_name)

            print(f"🎵 Extracting audio from: {os.path.basename(video_path)}")
            video_clip = VideoFileClip(video_path)
            
            if video_clip.audio is not None:
                # Save the individual audio file first
                video_clip.audio.write_audiofile(individual_mp3_path, logger=None)
                print(f"💾 Saved individual audio: {individual_mp3_path}")
                
                media_data["individual_audios"].append(os.path.abspath(individual_mp3_path))
                
                # Load back as an AudioClip or keep reference for concatenation with transitions
                audio_clips.append(video_clip.audio)
                saved_audio_paths.append(individual_mp3_path)
            else:
                print(f"⚠️ No audio track found in: {os.path.basename(video_path)}")
                video_clip.close()
                
        except Exception as e:
            print(f"❌ Failed to process {os.path.basename(video_path)}. Error: {e}")

    # 3. Concatenate with smooth transitions and write the final audio file
    if audio_clips:
        try:
            print("\n🔄 Applying smooth crossfade transitions and stitching audio tracks...")
            
            # Apply crossfade to clips for smooth audio blending (-transition_duration padding)
            # The first clip is left untouched, subsequent clips get a crossfade-in
            processed_clips = []
            for idx, clip in enumerate(audio_clips):
                if idx == 0:
                    processed_clips.append(clip)
                else:
                    # Apply fade in effect for smooth transition blending
                    processed_clips.append(clip.with_fadein(transition_duration))

            # Concatenate using negative padding to overlap the audio tracks for smooth crossfading
            final_audio = concatenate_audioclips(processed_clips, padding=-transition_duration)
            
            print(f"💾 Saving final master file to: {final_audio_path}")
            final_audio.write_audiofile(final_audio_path, logger=None)
            
            # Release final clip resources
            final_audio.close()
            print("✅ Final audio file created successfully with smooth transitions!")
            
        except Exception as e:
            print(f"❌ Error during audio merging and transitioning: {e}")
        finally:
            # Clean up all open audio tracks from memory
            for clip in audio_clips:
                clip.close()
    else:
        print("❌ No valid audio tracks were found to merge.")

    # Save data structure to JSON log file
    with open(output_json_name, 'w', encoding='utf-8') as json_file:
        json.dump(media_data, json_file, indent=4)
        
    print(f"📄 Log saved to: {os.path.abspath(output_json_name)}")

# --- Run the Program ---
if __name__ == "__main__":
    user_folder = r'C:\Ravi\Python'
    audios_folder = r'C:\Ravi\Python\audios'
    final_audio_file = r'C:\Ravi\Python\final_audio.mp3'
    
    create_audio_pipeline(
        input_folder=user_folder, 
        audios_output_dir=audios_folder,
        final_audio_path=final_audio_file,
        output_json_name="media_paths.json",
        transition_duration=1.0  # Adjust transition/crossfade duration in seconds here (e.g., 1.0 second)
    )
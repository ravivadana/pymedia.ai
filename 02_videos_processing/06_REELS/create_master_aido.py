import os
import numpy as np
from moviepy import AudioFileClip, concatenate_audioclips

def process_audios_from_folder(audios_folder, output_final_path, clip_duration=30.0, silence_threshold=0.001):
    if not os.path.exists(audios_folder):
        print(f"❌ Error: The folder '{audios_folder}' does not exist.")
        return

    # Gather all mp3 files in the audios folder
    audio_files = [os.path.join(audios_folder, f) for f in os.listdir(audios_folder) if f.lower().endswith('.mp3')]

    if not audio_files:
        print(f"❌ No MP3 audio files found in '{audios_folder}'.")
        return

    print(f"🔍 Found {len(audio_files)} audio files. Validating content and processing...")

    valid_audio_clips = []

    for file_path in audio_files:
        file_name = os.path.basename(file_path)
        try:
            # Load audio file
            audio_clip = AudioFileClip(file_path)

            # Check 1: Validate file duration exists and is greater than 0
            if audio_clip.duration is None or audio_clip.duration <= 0:
                print(f"⚠️ Skipping '{file_name}': Invalid or zero duration.")
                audio_clip.close()
                continue

            # Check 2: Validate audio content is not completely silent/empty
            # Sample audio frames to check RMS (Root Mean Square) volume level
            samples = audio_clip.to_soundarray(fps=11025) # low fps sample for quick check
            if samples is not None and len(samples) > 0:
                rms_volume = np.sqrt(np.mean(samples**2))
                if rms_volume < silence_threshold:
                    print(f"⚠️ Skipping '{file_name}': Audio content is completely silent (RMS: {rms_volume}).")
                    audio_clip.close()
                    continue
            else:
                print(f"⚠️ Skipping '{file_name}': Could not read audio samples.")
                audio_clip.close()
                continue

            # Content is verified and valid! Now truncate/extract up to clip_duration (30 seconds)
            target_duration = min(clip_duration, audio_clip.duration)
            sub_clip = audio_clip.subclipped(0, target_duration)
            
            valid_audio_clips.append(sub_clip)
            print(f"✅ Verified & Added: '{file_name}' ({target_duration:.1f}s)")

        except Exception as e:
            print(f"❌ Failed to process '{file_name}'. Error: {e}")

    # Concatenate valid clips and write final file
    if valid_audio_clips:
        try:
            print(f"\n🔄 Concatenating {len(valid_audio_clips)} valid audio clips...")
            final_audio = concatenate_audioclips(valid_audio_clips)
            
            print(f"💾 Saving final combined audio to: {output_final_path}")
            final_audio.write_audiofile(output_final_path, logger=None)
            
            final_audio.close()
            print("✅ 'concatedname_audio.mp3' created successfully!")

        except Exception as e:
            print(f"❌ Error during audio concatenation: {e}")
        finally:
            # Clean up loaded subclips from memory
            for clip in valid_audio_clips:
                clip.close()
    else:
        print("❌ No valid, non-silent audio files were found to concatenate.")

# --- Run the Program ---
if __name__ == "__main__":
    audios_source_folder = r'C:\Ravi\Python\audios'
    final_output_file = r'C:\Ravi\Python\concatedname_audio.mp3'
    
    process_audios_from_folder(
        audios_folder=audios_source_folder,
        output_final_path=final_output_file,
        clip_duration=30.0  # Extracts max 30 seconds from each audio
    )
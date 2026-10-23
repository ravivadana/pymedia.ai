from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import os
import re

def clean_transcript_text(text):
    # Replace bracketed words (e.g., [సంగీతం] or [Music]) with a newline character
    cleaned = re.sub(r'\[.*?\]', '\n', text)
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    return cleaned.strip()

def get_video_lyrics(video_url):
    try:
        video_id = None
        
        # 1. Handle Standard URLs (watch?v=)
        if "watch?v=" in video_url:
            video_id = video_url.split("watch?v=")[1].split("&")[0]
        # 2. Handle Short URLs (youtu.be/)
        elif "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1].split("?")[0]
        # 3. Handle YouTube Shorts URLs (/shorts/)
        elif "/shorts/" in video_url:
            video_id = video_url.split("/shorts/")[1].split("?")[0]
        else:
            raise ValueError("Invalid YouTube URL format.")

        print(f"Fetching Telugu lyrics for Video ID: {video_id}...\n")

        # Initialize API and fetch transcript specifying Telugu ('te')
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=['te', 'en'])

        # Format transcript to plain text without timestamps
        formatter = TextFormatter()
        lyrics_text = formatter.format_transcript(transcript)

        # Apply custom cleaning to replace brackets with newlines
        processed_lyrics = clean_transcript_text(lyrics_text)

        return processed_lyrics

    except Exception as e:
        return f"An error occurred: {e}"

# --- Example Usage ---
if __name__ == "__main__":
    url = "https://www.youtube.com/shorts/DEtHwz2qJvg" 
    
    lyrics = get_video_lyrics(url)
    
    print("--- LYRICS / TRANSCRIPT ---")
    print(lyrics)
    
    if not lyrics.startswith("An error occurred"):
        # Safely extract words for filename while preserving Unicode characters
        # Replace newlines with spaces temporarily to find the first words
        flat_text = lyrics.replace('\n', ' ')
        
        # Split by spaces and pick the first 5 words safely
        words = [w for w in flat_text.split() if w.strip()]
        first_five_words = "_".join(words[:5])
        
        # Remove any lingering symbols from the filename string safely
        first_five_words = re.sub(r'[^\w\s]', '', first_five_words)
        
        # Fallback if empty
        if not first_five_words:
            first_five_words = "telugu_lyrics"

        # Define directory and filename paths
        output_dir = "02_videos_processing/outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{output_dir}/{first_five_words}.txt"

        # Save to the text file
        with open(filename, "w", encoding="utf-8") as f:
            f.write(lyrics)
            
        print(f"\n[Saved successfully to {filename}]")
    else:
        print("\n[Skipped saving due to an error fetching lyrics.]")
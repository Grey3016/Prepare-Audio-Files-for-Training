import os
import time
import requests
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from bs4 import BeautifulSoup

# Required for reliable metadata reading
# Run: pip install music-tag
try:
    import music_tag
except ImportError:
    music_tag = None

# Fix for Python 3.13+ missing audioop
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
    except ImportError:
        audioop = None

from pydub import AudioSegment
# Note: We keep mediainfo imported for compatibility, but use music-tag for renaming
from pydub.utils import mediainfo

# --- CONFIGURATION ---
# Get your token at https://genius.com/api-clients
GENIUS_ACCESS_TOKEN = "YOUR_GENIUS_ACCESS_TOKEN_HERE" 

def clean_genius_junk(text):
    """Removes Genius metadata junk like 'Lyrics' prefix and leading whitespace."""
    lyrics_match = re.search(r'lyrics', text, re.IGNORECASE)
    if lyrics_match:
        text = text[lyrics_match.end():]
    bracket_index = text.find('[')
    if bracket_index != -1:
        return text[bracket_index:].strip()
    return text.strip()

def fetch_from_api(query):
    """Helper to perform the Genius API request with exponential backoff."""
    if not query.strip():
        return []
    
    search_url = "https://api.genius.com/search"
    headers = {'Authorization': f'Bearer {GENIUS_ACCESS_TOKEN}'}
    params = {'q': query}
    
    for attempt in range(3):
        try:
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('response', {}).get('hits', [])
            time.sleep(1)
        except Exception:
            time.sleep(1)
    return []

def get_lyrics_from_genius(filename):
    """Searches Genius using tiered strategies."""
    if not GENIUS_ACCESS_TOKEN or "YOUR_GENIUS" in GENIUS_ACCESS_TOKEN:
        return "ERROR: Genius API Token missing in script."

    parts = filename.split(" - ", 1)
    if len(parts) < 2:
        search_queries = [filename]
    else:
        artist_raw = parts[0]
        track_raw = parts[1]
        artist_clean = artist_raw.split(",")[0].strip()
        track_clean = re.sub(r'\(.*?\)', '', track_raw).strip()
        
        search_queries = [
            filename,                                       
            f"{artist_clean} - {track_raw}",                
            f"{artist_clean} - {track_clean}"               
        ]

    final_url = None
    for i, query in enumerate(search_queries):
        hits = fetch_from_api(query)
        if hits:
            final_url = hits[0]['result']['url']
            break

    if not final_url:
        return f"No Genius results found for: {filename}"

    try:
        page = requests.get(final_url, timeout=10)
        soup = BeautifulSoup(page.text, 'html.parser')
        lyric_containers = soup.select('div[class^="Lyrics__Container"], .lyrics')
        
        if not lyric_containers:
            return "Lyrics container not found on Genius page."

        raw_lyrics = ""
        for container in lyric_containers:
            for br in container.find_all("br"):
                br.replace_with("\n")
            raw_lyrics += container.get_text() + "\n"

        return clean_genius_junk(raw_lyrics)
    except Exception as e:
        return f"Error scraping lyrics: {str(e)}"

def run_processor():
    if not audioop:
        print("ERROR: 'audioop' module missing. Please run: pip install audioop-lts")
        return

    root = tk.Tk()
    root.withdraw()

    # 1. Select Directory
    source_dir = filedialog.askdirectory(title="Select Audio Folder")
    if not source_dir:
        return
    
    source_path = Path(source_dir)

    # 2. Ask to Rename based on Tags
    rename_prompt = (
        "Would you like to rename the original files based on their internal metadata tags?\n\n"
        "Format: 'Artist - Title.ext'\n\n"
        "IMPORTANT: Please ensure you are using a COPY of your original files before saying Yes, "
        "as this will modify the filenames in the folder."
    )
    do_rename = messagebox.askyesno("Rename Files?", rename_prompt)

    valid_exts = ('.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aiff')
    
    if do_rename:
        if music_tag is None:
            print("ERROR: 'music-tag' is required for renaming. Please run: pip install music-tag")
        else:
            print("Renaming original files based on metadata tags...")
            for file in source_path.iterdir():
                if file.suffix.lower() in valid_exts:
                    try:
                        f = music_tag.load_file(str(file))
                        artist = str(f['artist']).strip()
                        title = str(f['title']).strip()
                        
                        # Only proceed if both tags contain actual data
                        if artist and title and artist != 'None' and title != 'None':
                            new_stem = f"{artist} - {title}"
                            # Clean illegal filename characters
                            new_stem = re.sub(r'[\\/*?:"<>|]', "", new_stem)
                            new_file_path = file.parent / f"{new_stem}{file.suffix}"
                            
                            if file != new_file_path:
                                # Simple collision check
                                counter = 1
                                temp_path = new_file_path
                                while temp_path.exists():
                                    temp_path = file.parent / f"{new_stem} ({counter}){file.suffix}"
                                    counter += 1
                                new_file_path = temp_path
                                
                                file.rename(new_file_path)
                                print(f"Renamed: {file.name} -> {new_file_path.name}")
                    except Exception as e:
                        print(f"Error reading tags for {file.name}: {e}")

    # Refresh file list after potential renaming
    audio_files = [f for f in source_path.iterdir() if f.suffix.lower() in valid_exts]
    if not audio_files:
        print("No valid audio files found.")
        return

    # 3. Create Output Folder: [OriginalFolderName]_Processed
    output_path = source_path.parent / f"{source_path.name}_Processed"
    output_path.mkdir(exist_ok=True)

    print(f"\nPhase 1: Analyzing {len(audio_files)} files for relative volume...")
    loaded_data = []
    global_max_dbfs = -999.0

    for file in audio_files:
        try:
            seg = AudioSegment.from_file(file)
            loaded_data.append((file, seg))
            if seg.max_dBFS > global_max_dbfs:
                global_max_dbfs = seg.max_dBFS
        except Exception as e:
            print(f"Could not load {file.name}: {e}")

    if not loaded_data: 
        return
        
    target_gain = 0.0 - global_max_dbfs
    
    print("\nPhase 2: Normalizing (Relative), Resampling (48kHz), and Fetching Lyrics...")
    for file_path, seg in loaded_data:
        base_name = file_path.stem
        print(f"Processing: {base_name}")

        # Normalise relative to the set
        normalised_seg = seg.apply_gain(target_gain)
        
        # Resample to 48kHz
        normalised_seg = normalised_seg.set_frame_rate(48000)
        
        # Export WAV
        wav_output_path = output_path / f"{base_name}.wav"
        normalised_seg.export(wav_output_path, format="wav")
        
        # Lyrics
        lyrics = get_lyrics_from_genius(base_name)
        txt_output_path = output_path / f"{base_name}.txt"
        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write(lyrics)

        print(f"  - Created: {base_name}.wav (48kHz) & .txt")

    print(f"\nFinished! Processed files saved to:\n{output_path}")

if __name__ == "__main__":
    run_processor()
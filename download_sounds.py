#!/usr/bin/env python3
"""Download CC0 ambient sound loops from freesound.org for Central Park Walk.

Usage:
    python3 download_sounds.py

Requires a Freesound API key in FREESOUND_API_KEY env var, OR falls back to
generating silent placeholder WAV files so the game can load without errors.

Sound files are saved to sounds/ directory as WAV (audio_manager.gd loads WAV).
"""

import os
import struct

SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

# Required sound files and their freesound.org search queries
# audio_manager.gd expects .wav files in sounds/
SOUND_FILES = {
    "wind_trees.wav": "wind through trees loop",
    "city_distant.wav": "distant city traffic ambient",
    "water_lake.wav": "gentle lake water lapping",
    "water_fountain.wav": "fountain water splash",
    "footstep_grass.wav": "footstep grass single",
    "footstep_stone.wav": "footstep stone concrete single",
    "birds_daytime.wav": "birdsong forest loop",
}


def make_silent_wav(path: str, duration_s: float = 2.0, sample_rate: int = 44100) -> None:
    """Create a valid WAV file with silence.

    Generates a mono 16-bit PCM WAV that audio_manager.gd can parse and loop.
    """
    num_samples = int(sample_rate * duration_s)
    data_size = num_samples * 2  # 16-bit = 2 bytes per sample
    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # chunk size
        f.write(struct.pack("<H", 1))   # PCM format
        f.write(struct.pack("<H", 1))   # mono
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))  # byte rate
        f.write(struct.pack("<H", 2))   # block align
        f.write(struct.pack("<H", 16))  # bits per sample
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)  # silence


def main():
    os.makedirs(SOUNDS_DIR, exist_ok=True)

    api_key = os.environ.get("FREESOUND_API_KEY", "")

    if api_key:
        try:
            import requests
        except ImportError:
            print("requests not installed; generating silent placeholders")
            api_key = ""

    for filename, query in SOUND_FILES.items():
        filepath = os.path.join(SOUNDS_DIR, filename)
        if os.path.exists(filepath):
            print(f"  SKIP {filename} (already exists)")
            continue

        if api_key:
            try:
                import requests
                # Search for CC0 sounds, prefer WAV previews
                resp = requests.get(
                    "https://freesound.org/apiv2/search/text/",
                    params={
                        "query": query,
                        "filter": 'license:"Creative Commons 0"',
                        "fields": "id,name,previews",
                        "page_size": 1,
                        "token": api_key,
                    },
                    timeout=15,
                )
                data = resp.json()
                if data.get("results"):
                    previews = data["results"][0]["previews"]
                    # Prefer HQ MP3 preview, then convert; or just save OGG and note
                    preview_url = previews.get("preview-hq-mp3") or previews.get("preview-hq-ogg")
                    if preview_url:
                        audio = requests.get(preview_url, timeout=30)
                        # Save as-is (may be MP3/OGG — user should convert to WAV)
                        with open(filepath, "wb") as f:
                            f.write(audio.content)
                        print(f"  OK   {filename} <- freesound #{data['results'][0]['id']}")
                        print(f"         NOTE: may need conversion to WAV format")
                        continue
            except Exception as e:
                print(f"  WARN {filename}: freesound download failed ({e})")

        # Fallback: silent WAV placeholder
        print(f"  GEN  {filename} (silent WAV placeholder)")
        make_silent_wav(filepath)

    print(f"\nDone. {len(SOUND_FILES)} sound files in {SOUNDS_DIR}/")
    if not api_key:
        print("To get real sounds, set FREESOUND_API_KEY and re-run.")
        print("Or place your own WAV files (mono/stereo, 16-bit, 44100Hz) in sounds/")


if __name__ == "__main__":
    main()

import os
import sys
import json
from pathlib import Path

import requests
from dotenv import load_dotenv
import time


API_URL = "https://mangisoz.nu.edu.kz/backend/api/v1/diarization/analyze"
AUDIO_EXTS = {".mp3", ".wav", ".flac"}


def load_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("MANGISOZ_API_KEY")
    if not api_key:
        raise RuntimeError("MANGISOZ_API_KEY not found in .env")
    return api_key


def iter_audio_files(base_dir: Path):
    for p in sorted(base_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p


def diarize_file(audio_path: Path, api_key: str):
    headers = {"X-API-Key": api_key}
    data = {"tuning_json": ""}

    while True:
        with audio_path.open("rb") as f:
            files = {"audio": (audio_path.name, f, "audio/mpeg")}
            resp = requests.post(API_URL, headers=headers, data=data, files=files)

        if resp.status_code == 429:
            print("Received 429 (rate limited), waiting 10 seconds before retrying...")
            time.sleep(10)
            continue

        resp.raise_for_status()
        return resp.json()


def main():
    project_root = Path(__file__).resolve().parent
    default_audio_dir = project_root / "audio-test"

    if len(sys.argv) > 1:
        audio_paths = [Path(sys.argv[1])]
    else:
        audio_paths = list(iter_audio_files(default_audio_dir))

    if not audio_paths:
        print("No audio files found.")
        return

    api_key = load_api_key()

    for audio_path in audio_paths:
        print(f"Processing {audio_path}...")
        try:
            result = diarize_file(audio_path, api_key)
        except Exception as e:
            print(f"Error processing {audio_path}: {e}")
            continue

        out_path = audio_path.with_suffix(audio_path.suffix + ".json")
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Saved: {out_path}")
        time.sleep(4)


if __name__ == "__main__":
    main()
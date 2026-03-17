import os
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


STT_API_URL = "https://mangisoz.nu.edu.kz/backend/api/v1/stt/transcribe"
AUDIO_EXTS = {".mp3", ".wav", ".flac"}


def load_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("MANGISOZ_API_KEY")
    if not api_key:
        raise RuntimeError("MANGISOZ_API_KEY not found in .env")
    return api_key


def iter_clean_audios(clean_root: Path):
    for p in sorted(clean_root.rglob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p


def transcribe_file(audio_path: Path, api_key: str):
    headers = {"X-API-Key": api_key}
    data = {}  # use API defaults

    while True:
        with audio_path.open("rb") as f:
            files = {"audio": (audio_path.name, f, "audio/mpeg")}
            resp = requests.post(STT_API_URL, headers=headers, data=data, files=files)

        if resp.status_code == 429:
            print("Received 429 from STT API, waiting 10 seconds before retrying...")
            time.sleep(10)
            continue

        resp.raise_for_status()
        return resp.json()


def main():
    project_root = Path(__file__).resolve().parent
    clean_root = project_root / "clean"
    transcripts_root = project_root / "transcripts"

    if not clean_root.is_dir():
        print(f"'clean' directory not found at {clean_root}")
        return

    api_key = load_api_key()

    for audio_path in iter_clean_audios(clean_root):
        rel_path = audio_path.relative_to(clean_root)
        out_path = transcripts_root / rel_path
        out_path = out_path.with_suffix(out_path.suffix + ".json")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Transcribing {audio_path} -> {out_path}")
        try:
            result = transcribe_file(audio_path, api_key)
        except Exception as e:
            print(f"Error transcribing {audio_path}: {e}")
            continue

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # small pause between requests
        time.sleep(1)


if __name__ == "__main__":
    main()


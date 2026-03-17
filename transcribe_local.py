import os
import json
from pathlib import Path

import torch
import whisper


AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wav"}


def iter_cropped_audios(crops_root: Path):
    for p in sorted(crops_root.rglob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p


def load_whisper_model():
    """
    Load an OpenAI Whisper model for local transcription.

    You can override the default model via WHISPER_MODEL env var,
    e.g. WHISPER_MODEL=large-v3 or small, medium, large.
    """
    model_name = "medium"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Whisper model '{model_name}' on {device}...")
    model = whisper.load_model(model_name, device=device)
    return model


def transcribe_file_local(audio_path: Path, model):
    """
    Run Whisper transcription on a single audio file.
    """
    # You can set WHISPER_LANGUAGE to force a language, e.g. "kk" or "ru".
    kwargs = {}

    print(f"  Transcribing {audio_path}...")
    result = model.transcribe(str(audio_path), **kwargs)
    return result


def main():
    project_root = Path(__file__).resolve().parent
    base_root = project_root / "local_diarization"
    crops_root = base_root / "crops"
    transcripts_root = base_root / "transcripts"

    if not crops_root.is_dir():
        print(f"'crops' directory not found at {crops_root}")
        return

    audio_paths = list(iter_cropped_audios(crops_root))
    if not audio_paths:
        print("No cropped audio files found under local_diarization/crops.")
        return

    model = load_whisper_model()

    for audio_path in audio_paths:
        rel = audio_path.relative_to(crops_root)
        out_path = transcripts_root / rel
        out_path = out_path.with_suffix(out_path.suffix + ".json")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Skip if already transcribed
        if out_path.is_file():
            print(f"Skipping already transcribed: {out_path}")
            continue

        try:
            result = transcribe_file_local(audio_path, model)
        except Exception as e:
            print(f"Error transcribing {audio_path}: {e}")
            continue

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Saved transcript: {out_path}")


if __name__ == "__main__":
    main()


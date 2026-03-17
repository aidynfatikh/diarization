import os
import sys
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import subprocess
import librosa

from nemo.collections.asr.models import SortformerEncLabelModel

AUDIO_EXTS = {".mp3", ".wav", ".flac"}

def iter_audio_files(base_dir: Path):
    for p in sorted(base_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p

def load_audio_as_16k_mono(path: Path):
    """
    Load arbitrary audio (mp3/wav/flac) and return float32 mono at 16 kHz.
    """
    audio, sr = sf.read(str(path), always_2d=False)

    # Convert to mono if needed
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    # Ensure float32
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)

    target_sr = 16000
    if sr != target_sr:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        sr = target_sr

    return audio, sr


def load_model():
    """
    Load the NVIDIA Sortformer diarization model from Hugging Face..
    """
    model = SortformerEncLabelModel.from_pretrained("nvidia/diar_streaming_sortformer_4spk-v2")
    model.eval()

    # Example configuration matching "very high latency" from the model card.
    model.sortformer_modules.chunk_len = 340
    model.sortformer_modules.chunk_right_context = 40
    model.sortformer_modules.fifo_len = 40
    model.sortformer_modules.spkcache_update_period = 300
    model.sortformer_modules.spkcache_len = 188
    model.sortformer_modules._check_streaming_parameters()

    return model


def diarize_file_local(audio_path: Path, model: SortformerEncLabelModel):
    audio_np, sr = load_audio_as_16k_mono(audio_path)
    # Model expects list of arrays and explicit sample_rate for numpy input.
    predicted_segments = model.diarize(audio=[audio_np], batch_size=1, sample_rate=sr)

    # NeMo Sortformer.diarize() returns List[List[str]]: each segment is
    # a string "start end speaker_N" (see generate_diarization_output_lines in NeMo).
    segments_out = []
    for seg in predicted_segments[0]:
        s = seg if isinstance(seg, str) else None
        if s is None and isinstance(seg, (list, tuple)):
            s = " ".join(str(x) for x in seg)
        if not s or not s.strip():
            continue
        parts = s.split()
        if len(parts) < 3:
            continue
        try:
            start = float(parts[0])
            end = float(parts[1])
            speaker = parts[2]
            speaker_index = None
            if "_" in speaker:
                try:
                    speaker_index = int(speaker.split("_")[-1])
                except ValueError:
                    pass
        except (ValueError, TypeError):
            continue
        segments_out.append(
            {
                "start": start,
                "end": end,
                "speaker": speaker,
                "speaker_index": speaker_index,
            }
        )

    return {"data": {"segments": segments_out}}


def main():
    project_root = Path(__file__).resolve().parent
    default_audio_dir = project_root / "audio-test"
    out_root = project_root / "local_diarization"

    if len(sys.argv) > 1:
        audio_paths = [Path(sys.argv[1])]
    else:
        audio_paths = list(iter_audio_files(default_audio_dir))

    if not audio_paths:
        print("No audio files found.")
        return

    print("Loading NVIDIA Sortformer diarization model...")
    model = load_model()
    print("Model loaded.")

    for audio_path in audio_paths:
        print(f"Processing {audio_path}...")
        try:
            result = diarize_file_local(audio_path, model)
        except Exception as e:
            print(f"Error processing {audio_path}: {e}")
            continue

        # Mirror input structure inside out_root, append .json
        if audio_path.is_absolute():
            rel = audio_path.relative_to(default_audio_dir) if audio_path.is_relative_to(default_audio_dir) else audio_path.name
        else:
            rel = audio_path

        rel = Path(rel)
        out_path = out_root / rel
        out_path = out_path.with_suffix(out_path.suffix + ".json")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Saved JSON: {out_path}")

        # Also crop segments using the same logic as crop_from_json.py,
        # but keeping crops/clean inside local_diarization.
        segments = result.get("data", {}).get("segments") or []
        if not segments:
            continue

        audio_src = audio_path
        if not audio_src.is_file():
            print(f"Audio file not found for JSON: {audio_src}")
            continue

        crops_root = out_root / "crops"
        clean_root = out_root / "clean"
        out_dir = crops_root / audio_src.stem
        clean_dir = clean_root / audio_src.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        clean_dir.mkdir(parents=True, exist_ok=True)

        print(f"Writing crops to: {out_dir}")
        print(f"Writing clean crops to: {clean_dir}")

        for idx, seg in enumerate(segments, start=1):
            start = seg.get("start")
            end = seg.get("end")
            speaker = seg.get("speaker", "unknown")
            if start is None or end is None or end <= start:
                continue

            duration = end - start
            out_name = f"{idx:03d}_{speaker}{audio_src.suffix}"
            crop_path = out_dir / out_name
            print(f"  Segment {idx}: {start:.3f}s - {end:.3f}s -> {crop_path.name}")

            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start:.3f}",
                "-i",
                str(audio_src),
                "-t",
                f"{duration:.3f}",
                "-c",
                "copy",
                str(crop_path),
            ]
            try:
                subprocess.run(cmd, check=True)
                # Also store "clean" segments in 1.0–3.0 seconds range
                if 1.0 <= duration <= 3.0:
                    clean_path = clean_dir / out_name
                    print(f"    Copying to clean: {clean_path.name}")
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-ss",
                            f"{start:.3f}",
                            "-i",
                            str(audio_src),
                            "-t",
                            f"{duration:.3f}",
                            "-c",
                            "copy",
                            str(clean_path),
                        ],
                        check=True,
                    )
            except subprocess.CalledProcessError as e:
                print(f"    ffmpeg failed for segment {idx}: {e}")
                continue


if __name__ == "__main__":
    main()


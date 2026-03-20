import sys
import json
import os
import logging
from pathlib import Path
from multiprocessing import Process, Queue

import numpy as np
import soundfile as sf
import subprocess
import librosa
from tqdm import tqdm

os.environ["NEMO_LOG_LEVEL"] = "ERROR"
from nemo.collections.asr.models import SortformerEncLabelModel
from nemo.utils import logging as nemo_logging
nemo_logging.setLevel("ERROR")
logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)

AUDIO_EXTS = {".mp3", ".wav", ".flac"}
BATCH_SIZE = 8
NUM_CUT_WORKERS = 4


def iter_audio_files(base_dir: Path):
    for p in sorted(base_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p


def load_audio_as_16k_mono(path: Path) -> np.ndarray:
    audio, sr = sf.read(str(path), always_2d=False)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
    return audio


def load_model():
    model = SortformerEncLabelModel.from_pretrained("nvidia/diar_streaming_sortformer_4spk-v2")
    model.eval()
    model.sortformer_modules.chunk_len = 340
    model.sortformer_modules.chunk_right_context = 40
    model.sortformer_modules.fifo_len = 40
    model.sortformer_modules.spkcache_update_period = 300
    model.sortformer_modules.spkcache_len = 188
    model.sortformer_modules._check_streaming_parameters()
    return model


def _parse_segments(raw_segments):
    out = []
    for seg in raw_segments:
        parts = str(seg).split()
        if len(parts) != 3:
            continue
        try:
            start, end, speaker = float(parts[0]), float(parts[1]), parts[2]
        except (ValueError, TypeError):
            continue
        if end > start:
            out.append({"start": start, "end": end, "speaker": speaker})
    return out


def diarize_batch(audio_arrays: list, model) -> list:
    predicted = model.diarize(
        audio=audio_arrays,
        batch_size=len(audio_arrays),
        sample_rate=16000,
        verbose=False,
    )
    return [{"data": {"segments": _parse_segments(segs)}} for segs in predicted]


def cut_worker(job_queue: Queue, short_root: Path, long_root: Path):
    while True:
        job = job_queue.get()
        if job is None:
            return

        audio_src = Path(job["audio_path"])
        segments = job["segments"]
        short_dir = short_root / audio_src.stem
        long_dir = long_root / audio_src.stem
        short_dir.mkdir(parents=True, exist_ok=True)
        long_dir.mkdir(parents=True, exist_ok=True)

        for idx, seg in enumerate(segments, start=1):
            start, end, speaker = seg["start"], seg["end"], seg["speaker"]
            duration = end - start
            out_name = f"{idx:03d}_{speaker}{audio_src.suffix}"
            crop_path = short_dir / out_name if duration <= 2.0 else long_dir / out_name
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-ss", f"{start:.3f}", "-i", str(audio_src),
                "-t", f"{duration:.3f}", "-c", "copy", str(crop_path),
            ]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"ffmpeg failed segment {idx}: {e}")


def main():
    project_root = Path(__file__).resolve().parent
    default_audio_dir = project_root / "audio-test"
    out_root = project_root / "local_diarization"
    short_root = out_root / "short"
    long_root = out_root / "long"
    json_root = out_root / "jsons"

    if len(sys.argv) > 1:
        audio_paths = [Path(sys.argv[1])]
    else:
        audio_paths = list(iter_audio_files(default_audio_dir))

    json_root.mkdir(parents=True, exist_ok=True)
    audio_paths = [p for p in audio_paths if not (json_root / f"{p.name}.json").exists()]

    if not audio_paths:
        print("Nothing to process.")
        return

    short_root.mkdir(parents=True, exist_ok=True)
    long_root.mkdir(parents=True, exist_ok=True)

    model = load_model()

    job_queue = Queue(maxsize=64)
    cutters = [
        Process(target=cut_worker, args=(job_queue, short_root, long_root))
        for _ in range(NUM_CUT_WORKERS)
    ]
    for c in cutters:
        c.start()

    try:
        with tqdm(total=len(audio_paths), desc="Preparing audios") as pbar:
            for i in range(0, len(audio_paths), BATCH_SIZE):
                chunk_paths = audio_paths[i : i + BATCH_SIZE]
                audio_arrays = []
                for p in chunk_paths:
                    audio_arrays.append(load_audio_as_16k_mono(p))
                    pbar.update(1)

                results = diarize_batch(audio_arrays, model)

                for audio_path, result in zip(chunk_paths, results):
                    out_path = json_root / f"{audio_path.name}.json"
                    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
                    segments = result["data"]["segments"]
                    if segments:
                        job_queue.put({"audio_path": str(audio_path), "segments": segments})
    except Exception as e:
        print(f"Error: {e}")
    finally:
        for _ in cutters:
            job_queue.put(None)
        for c in cutters:
            c.join()


if __name__ == "__main__":
    main()

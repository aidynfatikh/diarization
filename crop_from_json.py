import json
import subprocess
from pathlib import Path


def crop_from_json(json_path: Path):
    print(f"Reading JSON: {json_path}")
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("data", {}).get("segments") or []
    if not segments:
        return

    audio_path = Path(json_path.with_suffix(""))  # strip only .json
    if not audio_path.is_file():
        print(f"Audio file not found for JSON: {audio_path}")
        return

    # Roots for all crops and "clean" crops
    base_root = json_path.parent.parent
    crops_root = base_root / "crops"
    clean_root = base_root / "clean"

    out_dir = crops_root / audio_path.stem
    clean_dir = clean_root / audio_path.stem

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
        out_name = f"{idx:03d}_{speaker}{audio_path.suffix}"
        out_path = out_dir / out_name
        print(f"  Segment {idx}: {start:.3f}s - {end:.3f}s -> {out_path.name}")

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(audio_path),
            "-t",
            f"{duration:.3f}",
            "-c",
            "copy",
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True)
            # Also store "clean" segments in 0.5–3.0 seconds range
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
                        str(audio_path),
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


def main():
    base_dir = Path(__file__).resolve().parent / "audio-test"
    print(f"Scanning for JSON files in: {base_dir}")
    for json_path in sorted(base_dir.glob("*.json")):
        crop_from_json(json_path)


if __name__ == "__main__":
    main()


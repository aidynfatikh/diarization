import shutil
from pathlib import Path

import soundfile as sf


AUDIO_EXTS = {".mp3", ".wav", ".flac"}


def move_jsons(old_root: Path, jsons_root: Path):
    jsons_root.mkdir(parents=True, exist_ok=True)
    skip_dirs = {"jsons", "short", "long", "crops", "clean"}

    moved = 0
    for json_path in old_root.rglob("*.json"):
        rel = json_path.relative_to(old_root)
        if not rel.parts:
            continue
        if rel.parts[0] in skip_dirs:
            continue

        rel = json_path.relative_to(old_root)
        dst = jsons_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(json_path), dst)
        moved += 1
        if moved % 5000 == 0:
            print(f"Moved JSONs: {moved}")
    print(f"Moved JSONs total: {moved}")


def copy_crops_to_short_long(old_root: Path, short_root: Path, long_root: Path):
    crops_root = old_root / "crops"
    if not crops_root.exists():
        return

    short_root.mkdir(parents=True, exist_ok=True)
    long_root.mkdir(parents=True, exist_ok=True)

    copied = 0
    for audio_path in crops_root.rglob("*"):
        if not audio_path.is_file() or audio_path.suffix.lower() not in AUDIO_EXTS:
            continue

        try:
            info = sf.info(str(audio_path))
        except Exception:
            continue

        duration = info.duration or 0.0
        rel = audio_path.relative_to(crops_root)
        dst = (short_root / rel) if duration <= 2.0 else (long_root / rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(audio_path, dst)
        copied += 1
        if copied % 5000 == 0:
            print(f"Copied crops: {copied}")
    print(f"Copied crops total: {copied}")


def main():
    old_root = Path.cwd() / "local_diarization"
    jsons_root = old_root / "jsons"
    short_root = old_root / "short"
    long_root = old_root / "long"

    move_jsons(old_root, jsons_root)
    copy_crops_to_short_long(old_root, short_root, long_root)
    print("Done.")


if __name__ == "__main__":
    main()

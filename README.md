# Audio test – diarization, cropping, transcription

Scripts for speaker diarization, segment cropping, and transcription. You can use either a **remote API** (Mangisož) or a **local pipeline** (NeMo Sortformer + Whisper).

---

## Directory layout

| Path | Description |
|------|-------------|
| `audio-test/` | Input full-length audio files (`.mp3`, `.wav`, `.flac`). Diarization JSONs are written next to them (e.g. `file.mp3.json`). |
| `clean/` | Short “clean” segments (1–3 s) from the **API/global** pipeline; used by the validator and `transcribe.py`. |
| `transcripts/` | Transcripts for files under `clean/` (API or manual pipeline). |
| `crops/` | All diarization segments from the **global** pipeline (when using `crop_from_json.py` on `audio-test`). |
| `local_diarization/` | Outputs of the **local** pipeline: diarization JSONs, `crops/`, `clean/`, `transcripts/`. |
| `validation_results.json` | Validator marks: `bad` / `maybe` per audio path (and mode). |
| `validator-ui/` | Next.js app to listen to clean segments and mark them bad/maybe. |

---

## Scripts

### 1. `diarize.py` – Diarization (remote API)

- **What it does:** Sends audio from `audio-test/` to the Mangisož diarization API and saves the response as `audio-test/<file>.mp3.json` (or `.wav.json` etc.).
- **Needs:** `pip install requests python-dotenv`, and a `.env` with `MANGISOZ_API_KEY=...`.
- **Run:**
  - All files in `audio-test/`:  
    `python diarize.py`
  - Single file:  
    `python diarize.py audio-test/myfile.mp3`

---

### 2. `diarize_local.py` – Diarization (local NeMo Sortformer)

- **What it does:** Runs the [NVIDIA Sortformer](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2) model locally on files in `audio-test/`, writes diarization JSONs under `local_diarization/`, and crops segments into `local_diarization/crops/` and `local_diarization/clean/` (clean = 1–3 s segments).
- **Needs:** NeMo (ASR), PyTorch, `soundfile`, `librosa`, `ffmpeg`, and a Hugging Face token for the model. Example setup:
  ```bash
  sudo apt-get install -y libsndfile1 ffmpeg
  pip install Cython packaging numpy soundfile librosa
  pip install 'torch'  # or CUDA build
  pip install 'git+https://github.com/NVIDIA/NeMo.git@main#egg=nemo_toolkit[asr]'
  huggingface-cli login
  ```
- **Run:**
  - All files in `audio-test/`:  
    `python diarize_local.py`
  - Single file:  
    `python diarize_local.py path/to/audio.mp3`

---

### 3. `crop_from_json.py` – Crop segments from diarization JSON (global)

- **What it does:** Reads diarization JSONs in `audio-test/*.json` (format `{"data": {"segments": [{"start", "end", "speaker"}, ...]}}`), finds the matching audio in the same folder, and cuts segments into `crops/<stem>/` and `clean/<stem>/` (clean only for duration 1–3 s). Uses `ffmpeg`.
- **Needs:** `ffmpeg` on PATH.
- **Run:**  
  `python crop_from_json.py`  
  (scans `audio-test/*.json`)

---

### 4. `transcribe.py` – Transcription (remote API)

- **What it does:** For each audio under `clean/`, calls the Mangisož STT API and saves the transcript as `transcripts/<same path>.json` (e.g. `transcripts/call_123/001_speaker_0.mp3.json`).
- **Needs:** `pip install requests python-dotenv`, `.env` with `MANGISOZ_API_KEY=...`.
- **Run:**  
  `python transcribe.py`

---

### 5. `transcribe_local.py` – Transcription (local Whisper)

- **What it does:** Transcribes every file under `local_diarization/crops/` with OpenAI Whisper and writes JSONs under `local_diarization/transcripts/` (same relative paths, `.json` appended).
- **Needs:** `pip install openai-whisper torch` (or `whisper`).
- **Env:** `WHISPER_MODEL` (default `medium`), optional `WHISPER_LANGUAGE` (e.g. `kk`, `ru`).
- **Run:**  
  `python transcribe_local.py`

---

### 6. `sample_marked_examples.py` – Sample “bad” segments for review

- **What it does:** Reads `validation_results.json`, collects paths marked `bad`, samples (e.g. one per call), and copies those audio files plus their transcripts into `sampled_marked_flat/` with a simple `transcripts.txt` listing.
- **Needs:** `clean/` and `transcripts/` populated; `validation_results.json` with `"bad"` entries.
- **Run:**  
  `python sample_marked_examples.py`

---

## Validator UI

- **What it does:** Web UI to play audio from `clean/` and mark segments as **Bad** or **Maybe**. Marks are stored in `validation_results.json`; keys are per-mode (e.g. `global:path` or `local:path`) so global and local pipelines don’t overlap.
- **Run:**
  ```bash
  cd validator-ui && npm install && npm run dev
  ```
  Then open the URL shown (e.g. http://localhost:3000).
- **Modes:** Use the top dropdown to switch between **clean/transcripts** (global) and **local_diarization** (local). In local mode, audio and pairs come from `local_diarization/clean/` and `local_diarization/transcripts/`.

---

## Typical workflows

**Remote (API) pipeline**

1. Put full-length audio in `audio-test/`.
2. `python diarize.py` → diarization JSONs next to each file.
3. `python crop_from_json.py` → `crops/`, `clean/`.
4. `python transcribe.py` → `transcripts/`.
5. Run `validator-ui` and mark in “Mode: clean/transcripts”.

**Local pipeline**

1. Put full-length audio in `audio-test/`.
2. `python diarize_local.py` → `local_diarization/*.json`, `local_diarization/crops/`, `local_diarization/clean/`.
3. `python transcribe_local.py` → `local_diarization/transcripts/`.
4. Run `validator-ui` and switch to “Mode: local_diarization” to validate.

**Sampling bad examples**

- After validating: `python sample_marked_examples.py` → `sampled_marked_flat/` with sampled “bad” segments and `transcripts.txt`.

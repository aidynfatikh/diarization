# Audio test – diarization, cropping, transcription

Scripts for speaker diarization, segment cropping, and transcription. You can use either a **remote API** (Mangisož) or a **local pipeline** (NeMo Sortformer + Whisper).

## Installation

1. **System:** Install `ffmpeg` and (for local diarization) `libsndfile1`, e.g. on Debian/Ubuntu:
   ```bash
   sudo apt-get update && sudo apt-get install -y ffmpeg libsndfile1
   ```

2. **Python:** Create a virtualenv, then install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Local diarization (optional):** If you use `diarize_local.py`, install NeMo and log in to Hugging Face:
   ```bash
   pip install Cython packaging
   pip install "git+https://github.com/NVIDIA/NeMo.git@main#egg=nemo_toolkit[asr]"
   huggingface-cli login
   ```

4. **Validator UI (optional):** For the web validator you need Node.js. From the project root:
   ```bash
   cd validator-ui && npm install
   ```

5. **API scripts (optional):** For `diarize.py` and `transcribe.py`, add a `.env` file with:
   ```
   MANGISOZ_API_KEY=your_key
   ```

## Files and usage

1. **diarize.py** – Sends audio from `audio-test/` to the Mangisož diarization API and saves each response as `audio-test/<filename>.mp3.json` (or the same base name with `.json` appended). Requires `MANGISOZ_API_KEY` in `.env`.  
   Run: `python diarize.py` for all files in `audio-test/`, or `python diarize.py path/to/audio.mp3` for one file.

2. **diarize_local.py** – Runs the NVIDIA Sortformer diarization model locally on files in `audio-test/`, writes diarization JSONs under `local_diarization/`, and crops segments into `local_diarization/crops/` and `local_diarization/clean/` (clean = 1–3 s). Needs NeMo and Hugging Face login.  
   Run: `python diarize_local.py` for all files, or `python diarize_local.py path/to/audio.mp3` for one file.

3. **crop_from_json.py** – Reads diarization JSONs in `audio-test/*.json` (with `data.segments` containing `start`, `end`, `speaker`), finds the matching audio in the same folder, and cuts segments with ffmpeg into `crops/<stem>/` and `clean/<stem>/` (clean only for 1–3 s duration).  
   Run: `python crop_from_json.py`.

4. **transcribe.py** – For each audio file under `clean/`, calls the Mangisož STT API and saves the transcript as `transcripts/<same relative path>.json`. Requires `MANGISOZ_API_KEY` in `.env`.  
   Run: `python transcribe.py`.

5. **transcribe_local.py** – Transcribes every file under `local_diarization/crops/` with OpenAI Whisper and writes JSONs under `local_diarization/transcripts/` (same relative paths with `.json` appended). Optional env: `WHISPER_MODEL` (default `medium`), `WHISPER_LANGUAGE` (e.g. `kk`, `ru`).  
   Run: `python transcribe_local.py`.

6. **sample_marked_examples.py** – Reads `validation_results.json`, collects paths marked `bad`, samples (e.g. one per call), and copies those audio files and their transcripts into `sampled_marked_flat/` with a `transcripts.txt` listing. Expects `clean/`, `transcripts/`, and `validation_results.json` with `bad` entries.  
   Run: `python sample_marked_examples.py`.

7. **validator-ui/** – Next.js app to play audio from `clean/` (or from `local_diarization/clean/` in local mode) and mark segments as Bad or Maybe. Marks are stored in `validation_results.json` with keys per mode (`global:path` or `local:path`).  
   Run: `cd validator-ui && npm run dev`, then open the URL shown (e.g. http://localhost:3000). Use the top dropdown to switch between “clean/transcripts” (global) and “local_diarization” (local).

## Typical workflows

**Remote (API) pipeline:** Put full-length audio in `audio-test/`. Run `python diarize.py`, then `python crop_from_json.py`, then `python transcribe.py`. Use validator-ui in “Mode: clean/transcripts” to validate.

**Local pipeline:** Put full-length audio in `audio-test/`. Run `python diarize_local.py`, then `python transcribe_local.py`. Use validator-ui in “Mode: local_diarization” to validate.

**Sampling bad examples:** After validating, run `python sample_marked_examples.py` to fill `sampled_marked_flat/` with sampled “bad” segments and `transcripts.txt`.

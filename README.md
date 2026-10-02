# WaveSeal

Audio forensics tool that detects tampering, splicing, and digital editing in audio recordings.

Upload any audio file to get a forensic verdict, a waveform with cut markers, and a downloadable PDF report.

---

## Features

- Splice detection: finds unnatural cut points in the waveform
- Room noise analysis: checks for background inconsistencies
- Digital silence detection: flags artificially inserted gaps
- Editor software tracing: detects known audio editor footprints in metadata
- Authenticity score: 0 to 100 percent based on a 5-pillar acoustic model
- PDF report: includes findings, waveform chart, and file hashes

---

## Run Locally

```bash
git clone https://github.com/PranavSarmukaddam/WaveSeal.git
cd WaveSeal
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Deploy to Streamlit Cloud

1. Push this repository to GitHub (`https://github.com/PranavSarmukaddam/WaveSeal.git`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**.
4. Select repository `PranavSarmukaddam/WaveSeal`, branch `main`, and main file path `app.py`.
5. Click **Deploy**. Streamlit installs `requirements.txt` and `packages.txt` automatically.

---

## Project Structure

```
waveseal/
├── app.py                     Web interface (Streamlit)
├── cli.py                     Command-line interface
├── requirements.txt           Python dependencies
├── packages.txt               System dependencies for deployment
├── .streamlit/
│   └── config.toml            Theme configuration
├── core/
│   ├── audio_processor.py     Signal loading, waveform, spectrogram
│   ├── tamper_detector.py     5-pillar forensic scoring engine
│   ├── metadata_extractor.py  File hashes, metadata, software tags
│   └── report_generator.py    PDF report generation
├── utils/
│   └── audio_generator.py     Built-in test audio samples
└── samples/                   Sample audio files
```

---

## CLI Usage

```bash
python cli.py path/to/audio.wav
```

---

## License & Copyright

Copyright (c) 2026 Pranav Sarmukaddam. All rights reserved. See [LICENSE](LICENSE) for terms.

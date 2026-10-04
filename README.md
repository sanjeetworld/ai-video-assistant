# AI Video Assistant

AI Video Assistant turns YouTube videos or local audio/video files into searchable meeting notes. It can transcribe English audio with local Whisper, translate Hinglish audio with Sarvam, generate summaries and action items with Mistral, and provide follow-up questions through a local RAG pipeline.

## Features

- Streamlit web interface in `app.py`
- Command-line pipeline in `main.py`
- YouTube and local media processing
- Whisper transcription for English
- Sarvam speech-to-text translation for Hinglish
- Mistral-powered title, summary, decisions, action items, and questions
- Local Chroma vector store for transcript Q&A

## Requirements

- Python 3.10 or newer
- FFmpeg installed and available on `PATH`
- A Mistral API key
- A Sarvam API key when using Hinglish transcription

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r Requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and add your own API keys. Never commit `.env` or real credentials.

## Run the web app

```powershell
streamlit run app.py
```

## Run the command-line pipeline

```powershell
python main.py
```

Enter a YouTube URL or a local media path when prompted.

## Project layout

```text
app.py                 Streamlit frontend
main.py                CLI pipeline
core/                  Transcription, summarization, extraction, and RAG
utils/                 Audio/video preprocessing
Requirements.txt       Python dependencies
test.py                Local test script
```

Generated media, vector databases, Python environments, caches, and secrets are intentionally excluded by `.gitignore`.

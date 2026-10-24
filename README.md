# AI Quiz Generator 2.0 — Neon Learning Lab

A gaming-inspired desktop quiz app with a modern web-style UI powered by Python + pywebview.

## Features
- Neon dark dashboard, responsive layout, custom challenge setup, quiz timer, feedback, results, answer review, history, and progress.
- AI generation for open-ended topics using OpenAI (`gpt-4o-mini`).
- PDF, DOCX, and TXT study-material upload.
- Strict source-only mode for uploaded study material: questions are accepted only when they include evidence that appears in the extracted material. If AI is not configured, material mode fails safely instead of substituting general questions.
- Offline sample bank for Python, Physics, and Biology.
- Quiz history stored locally in `data/history.json`.

## Setup (Windows PowerShell)
1. Install Python 3.10 or newer.
2. Open PowerShell in this project folder.
3. Install dependencies:
   ```powershell
   py -m pip install -r requirements.txt
   ```
4. Configure your OpenAI API key for AI mode (don't put the key in source code):
   ```powershell
   $env:OPENAI_API_KEY="your_api_key_here"
   ```
5. Run:
   ```powershell
   py main.py
   ```

Keep the PowerShell window open while using the app. The first launch may require an internet connection for the optional Google Fonts import; fallback fonts are used if those fonts aren't available.

## Notes
- Without an API key, only the bundled offline questions are available, and only for Python, Physics, and Biology.
- Strict study-material mode requires an API key. The app never silently falls back to general knowledge for uploaded material.
- The AI request currently samples up to four overlapping sections of long material to fit within a request. For very large documents, consider splitting by chapter for more exhaustive coverage.
- This package is a redesigned standalone implementation because the original source files were not attached in the conversation. You can replace files in your existing project after reviewing them, or run this folder separately.

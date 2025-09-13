# FastAPI Meet Companion (headless)

UI-less server to test your Google Meet CC pipeline:
- Send live captions to `POST /caption`
- Fetch rolling transcript with `GET /transcript`
- Ask Gemini for insights (JSON or SSE streaming)

## 1) Install & run
```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Set your Gemini key
set GEMINI_API_KEY=your_key_here   # Windows
# export GEMINI_API_KEY=your_key_here   # macOS/Linux

uvicorn app:app --reload --port 8765

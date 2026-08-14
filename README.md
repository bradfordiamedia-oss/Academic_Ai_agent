# Academic Agent

A Streamlit app with two AI-powered academic evaluation tools, backed by the
Claude API.

## Features

1. **Thesis Qualification Checker** — Upload your university's thesis
   guidelines and a thesis document. The agent checks the thesis against the
   guidelines and returns:
   - A qualification verdict (Qualified / Conditionally Qualified / Not Qualified)
   - An acceptance percentage
   - A full breakdown by criterion, strengths, weaknesses, and recommendations
   - A downloadable Markdown report

2. **Exam Auto-Grader** — Upload the exam questions, the official answer key,
   and a student's submitted answers. The agent grades each question, awards
   partial credit where appropriate, and returns:
   - Total score and percentage
   - Pass/fail against a threshold you choose
   - Per-question feedback
   - A downloadable Markdown report

Supported upload formats: PDF, DOCX, TXT, MD.

## Setup

```bash
git clone https://github.com/bradfordiamedia-oss/Academic_Ai_agent.git
cd Academic_Ai_agent
python -m venv .venv
.venv\Scripts\activate      # on Windows
pip install -r requirements.txt
copy .env.example .env      # then add your ANTHROPIC_API_KEY and APP_PASSWORD
```

## Run

```bash
streamlit run app.py
```

This opens the app in your browser. Pick a tool from the sidebar, upload the
required documents, and run the evaluation.

## Deploy to Streamlit Community Cloud

The app is ready to deploy as-is (Vercel is not compatible with Streamlit —
it needs a persistent server, not serverless functions).

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   the GitHub account that owns this repo.
2. Click **New app**, then pick:
   - Repository: `bradfordiamedia-oss/Academic_Ai_agent`
   - Branch: `main`
   - Main file path: `app.py`
3. Click **Advanced settings → Secrets** and paste:
   ```toml
   ANTHROPIC_API_KEY = "your_key_here"
   APP_PASSWORD = "choose_a_password"
   ```
   (see `.streamlit/secrets.toml.example` for the format — never commit real
   values to `secrets.toml` or `.env`, both are gitignored). `APP_PASSWORD`
   is the password visitors must enter on the login screen before they can
   use the app — pick anything, share it only with people you want to have
   access.
4. Click **Deploy**. The app builds from `requirements.txt` automatically.

## About the `api/` folder / `vercel.json`

These exist only so this repo can be imported into Vercel without the build
failing. Vercel hosts static sites and short-lived serverless functions, not
long-running processes — it cannot run Streamlit itself. Importing this repo
into Vercel deploys a small placeholder page (`api/index.py`) that explains
this and links back to the real app. The actual app runs via Streamlit Cloud
or locally, per the steps above.

## Project structure

```
Academic_Ai_agent/
├── app.py                   # Streamlit UI (both tools)
├── src/
│   ├── document_parser.py   # PDF/DOCX/TXT text extraction
│   ├── llm_client.py        # Anthropic API wrapper + JSON parsing
│   ├── thesis_evaluator.py  # Thesis qualification logic + prompt
│   ├── exam_grader.py       # Exam grading logic + prompt
│   └── ui.py                 # Theming/animation, login gate, percentage gauge
├── api/index.py             # Vercel placeholder landing page (see note above)
├── vercel.json               # Routes all Vercel traffic to the placeholder
├── requirements.txt
├── packages.txt              # apt package (tesseract-ocr) for scanned-PDF OCR
└── .env.example
```

## Notes

- Requires an `ANTHROPIC_API_KEY` (get one at console.anthropic.com).
- The app is gated behind a simple shared-password login screen
  (`APP_PASSWORD`). This is basic access control, not multi-user accounts —
  anyone with the password gets full access. Change it in Streamlit Cloud's
  Secrets whenever you want to revoke access.
- All evaluation happens per-request; no data is stored by the app itself.
- Grading/evaluation quality depends on how complete the uploaded guidelines
  and answer keys are — the more explicit the criteria, the more accurate
  the verdict.
- Scanned/photographed PDFs (no real text layer) are handled via OCR
  (Tesseract, through `pytesseract` + PyMuPDF) as a fallback when normal text
  extraction finds nothing. This requires the `tesseract-ocr` system package —
  already listed in `packages.txt` for Streamlit Cloud. Running locally, you
  need Tesseract installed separately (e.g. `winget install UB-Mannheim.TesseractOCR`
  on Windows, `apt install tesseract-ocr` on Linux, `brew install tesseract`
  on macOS) for OCR to work; without it, the app still runs fine for
  text-based PDFs/DOCX/TXT, just not scanned images.

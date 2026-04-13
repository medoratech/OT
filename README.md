# MEDORA OT

AI-powered OT (Operating Theatre) and OPD (Out-Patient Department) Clinical Documentation System.

## Features

- **OT Notes** — Voice-dictated, AI-structured operative notes with digital signature and PDF export
- **Consultations** — Doctor-patient voice recording with AI extraction of diagnosis, prescription, lab orders, and follow-up
- **Patient Registry** — Centralised patient records with MRN tracking
- **PDF Reports** — OT Note PDF & OPD Clinical Summary Report (3-page, medico-legal format)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python), SQLAlchemy async, PostgreSQL (Neon) |
| AI | Google Gemini 2.0 Flash (structuring) |
| STT | Deepgram (audio transcription) |
| Frontend | Vanilla JS SPA, ReportLab (PDF) |

## Setup

```bash
# 1. Clone and create venv
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Configure environment
cp backend/.env.example backend/.env
# Fill in DATABASE_URL, GEMINI_API_KEY, DEEPGRAM_API_KEY, JWT_SECRET

# 4. Run
cd backend && python -m uvicorn main:app --reload
```

## Environment Variables

See `backend/.env.example` for required keys.

---
Powered by **Gemini + Deepgram** | Built for clinical teams

# FoodVerse AI

Multimodal food-intelligence platform: React + FastAPI + Groq vision models.

| Module | What it does |
|---|---|
| Food Recognition | Photo/text/voice → identified food + **estimated** nutrition, confidence and limitations |
| Freshness Detector | Visible spoilage signs + storage context. Never certifies food as "safe" |
| Hygiene Monitor | Image or video (sampled frames via OpenCV) → observations, severity, indicative score, PDF report |
| Smart Kitchen | Ingredients text/photo/voice → structured recipe with safety notes |
| Meal Planner | Mifflin-St Jeor targets computed server-side, AI meals built around them, allergen check, weekly report |

## Architecture
```
frontend (React, Vite, Tailwind)  --HTTP/multipart-->  backend (FastAPI)
                                                         ├─ routers/   one per module
                                                         ├─ services/llm.py     lazy Groq client, JSON mode, fallbacks, error mapping
                                                         ├─ services/media.py   upload validation, video frames, audio
                                                         └─ services/schemas.py tolerant Pydantic types
```

## Prerequisites
Python 3.9+, Node 18+, and **ffmpeg** on PATH (only needed for voice notes). A Groq API key: https://console.groq.com

## Run it (Windows PowerShell)
```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # if blocked: Set-ExecutionPolicy -Scope Process Bypass
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env           # then edit .env and set GROQ_API_KEY
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Frontend (second terminal)
cd frontend
npm install
copy .env.example .env
npm run dev
```
App: http://localhost:5173 · API docs: http://localhost:8000/docs · Health: http://localhost:8000/health

## Configuration (`backend/.env`)
| Variable | Used by | Default |
|---|---|---|
| `GROQ_API_KEY` | all AI modules (required) | – |
| `GROQ_VISION_MODEL` | image modules | `qwen/qwen3.8-27b` |
| `GROQ_FALLBACK_MODELS` | tried if the primary is retired | Llama 4 Scout, Qwen 3.6 |
| `CORS_ORIGINS` | browser access | localhost:5173 |
| `MAX_UPLOAD_MB` / `MAX_VIDEO_MB` / `MAX_VIDEO_FRAMES` | upload limits | 10 / 60 / 6 |

Model IDs were checked against Groq's vision docs on 2026-10-27. Groq retires preview models often; if you see
"model unavailable", set `GROQ_VISION_MODEL` to a current vision model from the Groq docs.

## Endpoints
| Method | URL | Fields |
|---|---|---|
| POST | `/api/food-recognition/analyze` | `file`?, `text_context`?, `audio_file`? (at least one) |
| POST | `/api/freshness-detector/analyze` | `file`, `storage_time`?, `storage_type`?, `text_context`?, `audio_file`? |
| POST | `/api/hygiene-monitor/analyze` | `file` (image) **or** `video`, `context`? |
| POST | `/api/hygiene-monitor/report` | JSON `{result}` → PDF |
| POST | `/api/kitchen-assistant/generate-recipe` | `text_input`?, `file`?, `audio_file`? |
| POST | `/api/meal-planner/generate` | age, gender, height, weight, goals, activity_level, diet_type, cuisine, allergies, foods_to_avoid, medical_conditions, recent_history, weight_change |

Errors: 400/415/413 bad input · 422 validation · 429 rate limit · 502 bad model output · 503 missing/invalid key · 504 timeout.

## Tests
```powershell
cd backend
python -m pytest -q
```
20 tests, all AI calls mocked (no key or charges needed).

## Hygiene score
`100 − penalties` (High 15, Medium 8, Low 3), averaged over analysed frames. It is indicative only.

## Known limitations
- Photo-based nutrition and freshness are estimates; visual checks cannot detect pathogens.
- Hygiene review covers only the sampled frames; it is not real-time monitoring or a certified inspection.
- Voice notes use Google's free web speech recogniser (needs internet) and ffmpeg.
- "Recent analyses" on the dashboard is stored in your browser only.
- Live Groq calls were not exercised during development (no key available); behaviour is covered by mocked tests.

## Security
Keys come from env only. Uploads are decoded to validate, written to random temp names and deleted. CORS is restricted to configured origins. Do not commit `.env`.

# Boli – Real-time Speech to Text (Hindi + English)

Speak a sentence mixing Hindi and English and watch it transcribe live. Transcripts are stored in a
relational database and managed from a dashboard with full CRUD.

## Stack
| Layer | Choice |
|---|---|
| Backend | Python 3.11, FastAPI, WebSockets |
| Speech-to-text | **faster-whisper** (open-source Whisper, self-hosted, CPU, int8) |
| Database | PostgreSQL (SQLite fallback for local dev), SQLAlchemy 2 |
| Frontend | Vanilla JS, AudioWorklet (16 kHz PCM streaming) |
| Deploy | Docker (Hugging Face Spaces / Render / any VM) |

## How real-time works
1. Browser captures the mic with an `AudioWorklet`, resamples to 16 kHz mono Int16, and streams ~256 ms frames over a WebSocket.
2. Server buffers the current utterance and runs a simple energy-based voice-activity check.
3. Every ~1.5 s it decodes the buffer quickly (beam 1) and sends a grey **partial** result.
4. After ~0.9 s of silence (or 25 s max) it does a higher-quality decode (beam 5) and sends a **final** sentence.

### Hindi + English code-mixing
Whisper normally assumes one language per window. The "Hindi + English (mixed)" mode forces `language=hi`
and seeds `initial_prompt` with a Devanagari sentence that contains Latin-script English words, which
keeps words like *meeting*, *deadline* in English. Output is Devanagari Hindi + Latin English.
Other modes: Hindi, English, Auto-detect. Set `WHISPER_MODEL=medium` for better accuracy (needs more CPU/RAM).

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/transcriptions?q=` | List / search |
| POST | `/api/transcriptions` | Create |
| GET | `/api/transcriptions/{id}` | Read |
| PUT | `/api/transcriptions/{id}` | Update title/text |
| DELETE | `/api/transcriptions/{id}` | Delete |
| WS | `/ws/transcribe?lang=hi-en` | Live audio in, JSON out |
| GET | `/health` | Health check |

## Run locally
```bash
# Option A: Docker + Postgres
docker compose up --build        # http://localhost:8000

# Option B: plain Python (SQLite)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload    # http://localhost:8000
```
Mic access needs `localhost` or HTTPS.

## Environment variables
`DATABASE_URL`, `WHISPER_MODEL` (tiny/base/small/medium), `WHISPER_COMPUTE` (int8), `PRELOAD_MODEL` (1/0), `PORT`.

## Deploy (free options)
**Hugging Face Spaces (recommended – 16 GB RAM free, HTTPS):** create a new Space → SDK *Docker* → push this repo
(add `app_port: 7860` in the Space README front-matter). Add a free Postgres from Neon or Supabase and set
`DATABASE_URL` as a Space secret.

**Render:** New Web Service → connect GitHub repo → Runtime Docker → add `DATABASE_URL` (Render/Neon Postgres).
Use `WHISPER_MODEL=base` on small instances.

## Known limitations / next steps
- Energy-based VAD; swap for Silero VAD for noisy rooms.
- Whisper has no true streaming, so partials re-decode the buffer (cost grows with sentence length).
- No auth yet; add user accounts so history is per-user.
- Add Alembic migrations and tests for the WebSocket flow.

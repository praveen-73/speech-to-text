import asyncio
import json
import os
from pathlib import Path

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import stt
from .db import Base, engine, get_db
from .models import Transcription
from .schemas import TranscriptionIn, TranscriptionOut, TranscriptionUpdate

Base.metadata.create_all(engine)
app = FastAPI(title="Speech to Text")
STATIC = Path(__file__).parent / "static"

SAMPLE_RATE = 16000
SILENCE_RMS = 0.004          # energy threshold for "silence"
END_OF_UTTERANCE_SEC = 0.9   # this much silence finalises a sentence
PARTIAL_EVERY_SEC = 1.5      # how often to refresh the live partial
MAX_UTTERANCE_SEC = 25       # force-finalise very long run-ons


# @app.on_event("startup")
# async def warm_up():
#     if os.getenv("PRELOAD_MODEL", "1") == "1":
#         asyncio.get_event_loop().run_in_executor(None, stt.get_model)


@app.get("/health")
def health():
    return {"status": "ok", "model": stt.MODEL_SIZE}


# ---------------------------------------------------------------- CRUD
@app.get("/api/transcriptions", response_model=list[TranscriptionOut])
def list_items(q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Transcription).order_by(Transcription.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Transcription.text.ilike(like), Transcription.title.ilike(like)))
    return db.scalars(stmt).all()


@app.post("/api/transcriptions", response_model=TranscriptionOut, status_code=201)
def create_item(body: TranscriptionIn, db: Session = Depends(get_db)):
    item = Transcription(**body.model_dump())
    db.add(item)
    db.commit()
    return item


@app.get("/api/transcriptions/{item_id}", response_model=TranscriptionOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Transcription, item_id)
    if not item:
        raise HTTPException(404, "Transcription not found")
    return item


@app.put("/api/transcriptions/{item_id}", response_model=TranscriptionOut)
def update_item(item_id: int, body: TranscriptionUpdate, db: Session = Depends(get_db)):
    item = db.get(Transcription, item_id)
    if not item:
        raise HTTPException(404, "Transcription not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(item, k, v)
    db.commit()
    return item


@app.delete("/api/transcriptions/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Transcription, item_id)
    if not item:
        raise HTTPException(404, "Transcription not found")
    db.delete(item)
    db.commit()


# ---------------------------------------------------- real-time transcription
@app.websocket("/ws/transcribe")
async def ws_transcribe(ws: WebSocket, lang: str = "hi-en"):
    """
    Client streams raw 16 kHz mono Int16 PCM as binary frames.
    Send the text frame "flush" to finalise whatever is buffered (used on Stop).
    Server replies with JSON: {"type": "partial"|"final"|"level"|"info"|"flushed", "text": "..."}.
    """
    await ws.accept()
    buf: list[np.ndarray] = []      # audio of the utterance in progress
    has_speech = False
    silence = 0.0
    since_partial = 0.0
    busy = False
    closed = False

    async def send(payload: dict):
        """Send, but never crash if the browser already closed the socket."""
        nonlocal closed
        if closed:
            return
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            closed = True

    async def run(fast: bool, kind: str, audio: np.ndarray):
        nonlocal busy
        try:
            text = await asyncio.to_thread(stt.transcribe, audio, lang, fast)
            if text:
                await send({"type": kind, "text": text})
            elif kind == "final":
                await send({"type": "info", "text": "Heard audio but no words were recognised. Speak closer and louder."})
        except Exception as e:  # keep the socket alive on model errors
            await send({"type": "error", "text": str(e)})
        finally:
            if kind == "partial":
                busy = False

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break

            if msg.get("text") == "flush":
                if has_speech and buf:
                    audio = np.concatenate(buf)
                    buf, has_speech, silence, since_partial = [], False, 0.0, 0.0
                    await run(False, "final", audio)
                await send({"type": "flushed"})
                continue

            data = msg.get("bytes")
            if not data:
                continue
            chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            dur = len(chunk) / SAMPLE_RATE
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            loud = rms > SILENCE_RMS
            await send({"type": "level", "rms": round(rms, 4), "speech": loud})

            if loud:
                has_speech, silence = True, 0.0
            elif has_speech:
                silence += dur
            else:
                continue  # leading silence: ignore

            buf.append(chunk)
            since_partial += dur
            total = sum(len(c) for c in buf) / SAMPLE_RATE

            if silence >= END_OF_UTTERANCE_SEC or total >= MAX_UTTERANCE_SEC:
                audio = np.concatenate(buf)
                buf, has_speech, silence, since_partial = [], False, 0.0, 0.0
                await run(False, "final", audio)
            elif since_partial >= PARTIAL_EVERY_SEC and not busy:
                since_partial = 0.0
                busy = True
                asyncio.create_task(run(True, "partial", np.concatenate(buf)))
    except (WebSocketDisconnect, RuntimeError):
        pass


# ------------------------------------------------------------------ frontend
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
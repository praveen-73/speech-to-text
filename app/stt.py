"""Speech-to-text via Groq's hosted Whisper (no local model, no disk usage)."""
import io
import os
import wave

import numpy as np
import requests
from dotenv import load_dotenv
load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
# whisper-large-v3 = best accuracy; whisper-large-v3-turbo = faster/cheaper
MODEL_ACCURATE = os.getenv("WHISPER_MODEL", "whisper-large-v3")
MODEL_FAST = os.getenv("WHISPER_MODEL_FAST", "whisper-large-v3-turbo")

# Mixing Devanagari Hindi with Latin-script English nudges Whisper to keep
# English words in English instead of transliterating them.
HINGLISH_PROMPT = "मैं आज office में meeting attend करने जा रहा हूँ, project का deadline tomorrow है।"


def _to_wav_bytes(audio: np.ndarray, sample_rate: int = 16000) -> bytes:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def transcribe(audio: np.ndarray, language: str = "hi-en", fast: bool = False) -> str:
    """audio: float32 mono, 16 kHz, range [-1, 1]."""
    if audio.size < 8000:  # <0.5 s, nothing useful
        return ""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    data = {
        "model": MODEL_FAST if fast else MODEL_ACCURATE,
        "response_format": "json",
        "temperature": "0",
    }
    if language == "hi-en":
        data["language"] = "hi"
        data["prompt"] = HINGLISH_PROMPT
    elif language != "auto":
        data["language"] = language

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        files={"file": ("audio.wav", _to_wav_bytes(audio), "audio/wav")},
        data=data,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("text", "").strip()
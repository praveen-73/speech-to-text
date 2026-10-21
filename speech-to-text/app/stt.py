"""Self-hosted speech-to-text using faster-whisper (open-source Whisper, CTranslate2)."""
import os
import threading
import numpy as np

MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")  # tiny / base / small / medium / large-v3
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")

# A prompt that mixes Devanagari Hindi with Latin-script English nudges Whisper to
# keep English words in English instead of transliterating them into Devanagari.
HINGLISH_PROMPT = "मैं आज office में meeting attend करने जा रहा हूँ, project का deadline tomorrow है।"

_model = None
_lock = threading.Lock()  # one decode at a time; keeps CPU usage predictable


def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE)
    return _model


def transcribe(audio: np.ndarray, language: str = "hi-en", fast: bool = False) -> str:
    """audio: float32 mono, 16 kHz, range [-1, 1]."""
    if audio.size < 8000:  # <0.5 s, nothing useful
        return ""
    if language == "hi-en":
        lang, prompt = "hi", HINGLISH_PROMPT
    elif language == "auto":
        lang, prompt = None, None
    else:
        lang, prompt = language, None

    with _lock:
        segments, _ = get_model().transcribe(
            audio,
            language=lang,
            initial_prompt=prompt,
            beam_size=1 if fast else 5,
            vad_filter=True,
            vad_parameters=dict(threshold=0.3, min_silence_duration_ms=500),
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()

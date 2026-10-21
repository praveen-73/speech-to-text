FROM python:3.11-slim
WORKDIR /code
ENV PYTHONUNBUFFERED=1 HF_HOME=/code/.cache
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ARG WHISPER_MODEL=small
ENV WHISPER_MODEL=${WHISPER_MODEL}
# bake the model into the image so cold starts are fast
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8')"
COPY app ./app
EXPOSE 7860
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]

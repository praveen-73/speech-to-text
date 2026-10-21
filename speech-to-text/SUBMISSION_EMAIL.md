To: prerna.shrivastava@procucev.com
Cc: anshul.goel@procucev.com
Subject: Assignment 1 Submission – Real-time Transcription (Speech to Text)

Hi Prerna,

Please find my submission for Assignment 1 (Real-time Transcription).

GitHub repository: <PASTE GITHUB LINK>
Deployed application: <PASTE DEPLOYED LINK>

Summary
- Stack: Python / FastAPI, WebSockets, PostgreSQL, vanilla JS (AudioWorklet)
- Speech-to-text: faster-whisper (open-source Whisper, self-hosted), tuned for Hindi + English code-mixed speech
- Real-time: mic audio streamed at 16 kHz over WebSocket; live partial results, finalised on silence
- Dashboard: save, search, edit, copy and delete transcripts (full CRUD, REST API)
- Setup and design notes are in the README

Known limitations: energy-based VAD, no authentication, partial results re-decode the buffer.

Regards,
<Your name>
<Phone> | <LinkedIn/GitHub>

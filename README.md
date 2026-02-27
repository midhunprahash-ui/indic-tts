# Tanglish TTS Playground

Production-style demo app to compare Tanglish/Tamil/English TTS models side-by-side with strict fault isolation.

## What was built

- Monorepo layout:
  - `frontend/` React + Vite + TypeScript
  - `backend/` FastAPI + layered adapter architecture
- Backend layered design:
  - `domain/` contracts, entities, errors
  - `application/` orchestration + timeout/isolation services
  - `infrastructure/` provider adapters + env/config + audio storage
- Exact requested model catalog:
  - Cloud (9):
    - Sarvam `bulbul:v3-beta`
    - Sarvam `bulbul:v2`
    - Google `en-IN-Chirp3-HD`
    - Google `ta-IN-Neural2-D`
    - Azure `ta-IN-SwetaNeural`
    - Azure `en-IN-NeerjaNeural`
    - Amazon AWS `en-IN-SeemaNeural`
    - Amazon AWS `ta-IN-RamyaNeural`
    - ElevenLabs `Adam (Indian accent)`
  - Self-hosted (2):
    - `ai4bharat/indic-parler-tts`
    - `maya-research/veena-all-v1`
- One adapter class per model + shared runtime helpers.
- API endpoints:
  - `GET /health`
  - `GET /models/catalog`
  - `POST /tts/synthesize`
  - `POST /tts/synthesize-batch`
  - `GET /tts/audio/{audio_id}`
- Strong isolation:
  - per-model timeout
  - per-adapter exception handling
  - batch returns partial success; one failure never breaks others
- Frontend UX:
  - grouped top tabs: Cloud + Self-hosted
  - left sidebar dynamic config form from backend schema
  - center text composer + single/batch actions
  - per-model output cards with status, latency, audio, error
- Environment awareness:
  - model-specific `configured` + warnings in catalog and UI
  - missing credentials never crash app
- Tests:
  - backend isolation + partial success
  - frontend tab rendering + partial failure handling

## Architecture notes

- Streaming is attempted where practical/available, then auto-fallback to REST/non-streaming.
- Unified result envelope per model:
  - `model_id`
  - `success`
  - `audio_url` / `audio_base64`
  - `latency_ms`
  - `streaming_used`
  - `error`
- Self-hosted adapters use lazy local HF runtime loading with graceful dependency/model errors.

## Prerequisites

- Python `3.11+` (recommended; verified on `3.11.14`)
- Node.js `18+`
- npm `9+`
- Docker Desktop (for `docker compose` flow)

## Docker Compose (one command)

Run both apps together:

```bash
docker compose up --build
```

Endpoints:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

Run in background:

```bash
docker compose up --build -d
```

Stop and remove containers:

```bash
docker compose down
```

Notes:

- Compose passes provider credentials from your shell environment (e.g. `SARVAM_API_KEY`, `AZURE_SPEECH_KEY`).
- If credentials are missing, the app still starts and marks models as not configured.
- Self-hosted HF adapters are implemented; heavy local runtime libraries are not installed in the default Docker image.

## Backend setup

```bash
cd backend
cp .env.example .env
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional self-hosted runtime dependencies:

```bash
pip install -r requirements-self-hosted.txt
```

Run backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`

## Environment files

- Backend template: `backend/.env.example`
- Frontend template: `frontend/.env.example`

## API quick checks

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/models/catalog | jq '.models | length'
```

Single model synth:

```bash
curl -s -X POST http://localhost:8000/tts/synthesize \
  -H 'Content-Type: application/json' \
  -d '{
    "model_id": "sarvam:bulbul:v2",
    "text": "Vanakkam, this is a Tanglish TTS check",
    "config_overrides": {"target_language_code": "en-IN", "speaker": "anushka"},
    "prefer_streaming": true
  }' | jq
```

Batch synth:

```bash
curl -s -X POST http://localhost:8000/tts/synthesize-batch \
  -H 'Content-Type: application/json' \
  -d '{
    "model_ids": ["sarvam:bulbul:v2", "aws:en-IN-SeemaNeural", "elevenlabs:Adam-Indian-accent"],
    "text": "This should speak on all selected models",
    "per_model_config": {},
    "prefer_streaming": true
  }' | jq
```

## Streaming vs fallback matrix

- `sarvam:bulbul:v2`: WebSocket streaming first, REST fallback.
- `sarvam:bulbul:v3-beta`: REST implementation (streaming support unclear in surfaced docs).
- `google:en-IN-Chirp3-HD`: streaming attempt (client), REST fallback.
- `google:ta-IN-Neural2-D`: streaming attempt (client), REST fallback.
- `azure:ta-IN-SwetaNeural`: SDK streaming-style synthesis attempt, REST fallback.
- `azure:en-IN-NeerjaNeural`: SDK streaming-style synthesis attempt, REST fallback.
- `aws:en-IN-SeemaNeural`: Polly synthesize API (REST style).
- `aws:ta-IN-RamyaNeural`: Polly synthesize API (REST style).
- `elevenlabs:Adam-Indian-accent`: streaming endpoint first, convert endpoint fallback.
- `ai4bharat/indic-parler-tts`: local self-hosted runtime (non-streaming).
- `maya-research/veena-all-v1`: local self-hosted runtime (non-streaming), aliased by default to `maya-research/Veena`.

## Model-specific limitations

- Free-tier/provider access limits vary by account and region.
- `bulbul:v3-beta` availability may require explicit provider-side enablement.
- Google and Azure require proper cloud permissions for selected voices.
- AWS Polly voices/engines vary by region; if a requested voice-engine combo is unsupported in your account region, adapter returns a model-level error.
- ElevenLabs `Adam (Indian accent)` depends on configured `ELEVENLABS_ADAM_VOICE_ID` and plan limits for selected output format.
- Self-hosted HF models may require extra runtime dependencies and/or model-specific code; adapters fail gracefully with actionable errors when unavailable.

## Quick model testing guide

1. Start backend + frontend.
2. Open UI, paste text, choose a model tab.
3. Confirm sidebar shows configured state.
4. Click `Speak` for single model.
5. Select multiple checkboxes in tabs and click `Speak on selected models`.
6. Verify independent status cards and audio playback.

Recommended smoke text:

```text
Vanakkam! Naan inikku Tanglish TTS demo test panren. Please speak this clearly.
```

## Tests

Backend tests:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Frontend tests:

```bash
cd frontend
npm run test
npm run build
```

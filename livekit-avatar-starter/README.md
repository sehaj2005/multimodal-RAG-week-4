# Realtime AI Avatar — MVP starter

Implements the proposal's first milestones: FastAPI room/token service, React meeting shell, LiveKit voice agent, optional Simli avatar. **Not production ready**: the demo API has no user authentication, authorization, persisted meetings or rate limits; do not expose to the public internet.

## Prerequisites
- Python 3.11+ recommended, Node.js 20+, LiveKit Cloud project, Deepgram, OpenAI, Cartesia credentials.
- Simli API key and face ID when you enable the video avatar.
- Agent needs working cloud dispatch registration; local dev should run a worker that is registered under `avatar-agent`. Check the LiveKit CLI documentation if your dev deployment is isolated.

## 1. Configure
Copy `.env.example` to `.env` and fill the keys. Leave `ENABLE_SIMLI=false` for voice-only Phase B.

## 2. Start backend (Windows PowerShell)
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-backend.txt
uvicorn backend.main:app --reload --port 8000
```

## 3. Start agent (a second PowerShell terminal)
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-agent.txt
python agent/agent.py dev
```

For modern LiveKit CLI workflows, `lk agent dev` is also supported when the CLI is configured. Explicit dispatch may target a deployment; if your dev worker is scoped to a nonproduction deployment, adjust dispatch configuration to match it.

## 4. Start frontend (third PowerShell terminal)
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. Browser permission prompts for camera/mic require allowing access.

## 5. Enable Simli (after voice works)
- Select a Simli face in your account and set `SIMLI_FACE_ID` and `SIMLI_API_KEY` in `.env`.
- Set `ENABLE_SIMLI=true` and restart the agent worker.
- Confirm the avatar's video and **one** audio path are visible/audible in the room.
- Use the LiveKit docs to tune the latest avatar/audio output configuration; no credentials belong in frontend code.

## Verify
- GET http://localhost:8000/health returns `{"status":"ok"}`.
- POST `/api/v1/meetings` returns new room metadata.
- POST `/api/v1/meetings/{meeting_id}/join` returns a short-lived participant JWT.
- Start worker and request agent start: confirm agent joins, speaks and responds to interruptions.

## Deferred endpoints & work
The proposal's agent stop, meeting end, transcript logging, telemetry, identity/permissions, persistent storage, and production rate limiting are deliberately excluded from this starter. The agent start endpoint is only a local demo dispatch. In production add authentication and room-owner authorization to every endpoint, ensure secure room lifecycle, avoid duplicate dispatch under concurrency, and revoke participant access properly.

References: https://docs.livekit.io/agents/start/voice-ai/ , https://docs.livekit.io/agents/models/avatar/plugins/simli/ , https://docs.livekit.io/agents/server/agent-dispatch/

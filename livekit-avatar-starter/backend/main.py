
import os
import uuid
from datetime import timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from livekit import api


# ==========================================
# 1. Load environment variables
# ==========================================

load_dotenv(".env")


# ==========================================
# 2. Initialize FastAPI
# ==========================================

app = FastAPI(
    title="Realtime AI Avatar API",
    description="FastAPI backend for LiveKit and Simli AI Avatar",
    version="1.0.0",
)


# ==========================================
# 3. CORS Configuration
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ==========================================
# 4. Temporary Meeting Storage
# ==========================================

meetings = {}


# ==========================================
# 5. Request Models
# ==========================================

class JoinRequest(BaseModel):
    display_name: str = Field(
        default="Guest",
        min_length=1,
        max_length=80
    )
    role: str = "human"


# ==========================================
# 6. Health Check
# ==========================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Realtime AI Avatar Backend"
    }


# ==========================================
# 7. Readiness Check
# ==========================================

@app.get("/ready")
def ready():
    required = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ]

    configured = all(
        bool(os.getenv(key)) for key in required
    )

    return {"ready": configured}


# ==========================================
# 8. Create Meeting
# ==========================================

@app.post("/api/v1/meetings")
def create_meeting():

    meeting_id = "mtg_" + uuid.uuid4().hex[:12]
    room_name = "room_" + uuid.uuid4().hex[:12]

    meeting = {
        "meeting_id": meeting_id,
        "room_name": room_name,
        "state": "created",
    }

    meetings[meeting_id] = meeting

    return meeting


# ==========================================
# 9. Get Meeting Details
# ==========================================

@app.get("/api/v1/meetings/{meeting_id}")
def get_meeting(meeting_id: str):

    meeting = meetings.get(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="Meeting not found"
        )

    return meeting


# ==========================================
# 10. Join LiveKit Meeting
# ==========================================

@app.post("/api/v1/meetings/{meeting_id}/join")
def join_meeting(
    meeting_id: str,
    body: JoinRequest
):

    meeting = meetings.get(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="Meeting not found"
        )

    if meeting["state"] == "ended":
        raise HTTPException(
            status_code=410,
            detail="Meeting has ended"
        )

    if body.role != "human":
        raise HTTPException(
            status_code=403,
            detail="Only human participants can join"
        )

    required = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ]

    if not all(os.getenv(key) for key in required):
        raise HTTPException(
            status_code=503,
            detail="LiveKit credentials are missing"
        )

    participant_id = (
        "human_" + uuid.uuid4().hex[:12]
    )

    token = (
        api.AccessToken(
            os.environ["LIVEKIT_API_KEY"],
            os.environ["LIVEKIT_API_SECRET"]
        )
        .with_identity(participant_id)
        .with_name(body.display_name)
        .with_ttl(timedelta(minutes=15))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=meeting["room_name"],
                can_publish=True,
                can_subscribe=True
            )
        )
        .to_jwt()
    )

    return {
        "meeting_id": meeting_id,
        "room_name": meeting["room_name"],
        "participant_id": participant_id,
        "livekit_url": os.environ["LIVEKIT_URL"],
        "access_token": token,
        "expires_in": 900,
    }


# ==========================================
# 11. Start AI Agent
# ==========================================

@app.post(
    "/api/v1/meetings/{meeting_id}/agent/start"
)
async def start_agent(meeting_id: str):

    meeting = meetings.get(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="Meeting not found"
        )

    if meeting["state"] == "ended":
        raise HTTPException(
            status_code=410,
            detail="Meeting has ended"
        )

    livekit = None

    try:
        livekit = api.LiveKitAPI()

        existing = await livekit.agent_dispatch.list_dispatch(
    meeting["room_name"]
)

        matches = [
            dispatch
            for dispatch in existing
            if dispatch.agent_name == "avatar-agent"
        ]

        if matches:
            return {
                "dispatch_id": matches[0].id,
                "status": "already_dispatched",
            }

        dispatched = await livekit.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
        room=meeting["room_name"],
        agent_name="avatar-agent",
    )
)

        meeting["state"] = "agent_requested"

        return {
            "dispatch_id": dispatched.id,
            "status": "requested",
        }

    except Exception as error:
        print(f"LiveKit Agent Error: {error}")

        raise HTTPException(
            status_code=502,
            detail="Unable to dispatch AI agent"
        )

    finally:
        if livekit is not None:
            await livekit.aclose()


# ==========================================
# 12. Meeting Status
# ==========================================

@app.get(
    "/api/v1/meetings/{meeting_id}/status"
)
def meeting_status(meeting_id: str):

    return get_meeting(meeting_id)


# ==========================================
# Development-only backend.
# No authentication or persistent database.
# Do not expose publicly.
# ==========================================

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

from mood_mappings import (
    MOOD_INTENSITY_MAP,
    get_intensity_range,
    FRONTEND_TO_BACKEND_MOOD,
    FRONTEND_INTENSITY_TO_NUMBER,
)
from audio_archive_service import archive_service, WellnessTrack


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Soundlull Mood Wellness API")
api_router = APIRouter(prefix="/api")


# ---------- Static catalog (display data for the wizard UI) ----------

MOODS = [
    {"id": "stressed",   "label": "Seeking Serenity",  "subtitle": "Stressed",   "icon": "Wind",     "description": "Soften the edges of a heavy day."},
    {"id": "unfocused",  "label": "Seeking Clarity",   "subtitle": "Unfocused",  "icon": "Droplets", "description": "Settle scattered thoughts into one quiet stream."},
    {"id": "low_energy", "label": "Seeking Renewal",   "subtitle": "Low Energy", "icon": "Sun",      "description": "Invite warmth back into your body."},
    {"id": "anxious",    "label": "Seeking Grounding", "subtitle": "Anxious",    "icon": "Mountain", "description": "Return to the steady earth beneath you."},
    {"id": "restless",   "label": "Seeking Peace",     "subtitle": "Restless",   "icon": "Feather",  "description": "Let the body slow to the breath."},
]

INTENSITIES = [
    {"id": "gentle",    "label": "Gentle",    "description": "Whisper-soft, barely there."},
    {"id": "mild",      "label": "Mild",      "description": "A light, easy embrace."},
    {"id": "balanced",  "label": "Balanced",  "description": "Even, grounding presence."},
    {"id": "deep",      "label": "Deep",      "description": "Immersive resonance."},
    {"id": "immersive", "label": "Immersive", "description": "Full, enveloping landscape."},
]

DURATIONS = [5, 10, 15, 20, 30]


# ---------- Schemas ----------

class WellnessGenerateRequest(BaseModel):
    """Matches the Node backend contract:
    POST /api/music-wellness/generate
    """
    currentMood: str = Field(..., min_length=1)
    intensity: int
    desiredMood: str = Field(default="Calm")
    musicPreferences: List[str] = Field(default_factory=list)
    sessionDuration: int = Field(default=15)


class TrackOut(BaseModel):
    id: str
    title: str
    artist: str
    duration: int
    audioUrl: str


class WellnessGenerateResponse(BaseModel):
    sessionId: str
    currentMood: str
    intensity: int
    intensityBucket: str
    desiredMood: str
    sessionDuration: int
    searchQuery: str
    targetTags: List[str]
    tracks: List[TrackOut]


# ---------- Helpers ----------

def _validate_intensity(value: int) -> None:
    if not isinstance(value, int) or value < 1 or value > 5:
        raise _validation_error("intensity must be an integer between 1 and 5")


def _validation_error(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"error": "ValidationError", "message": detail})


async def _generate_tracks(
    mood_name: str, intensity: int, session_duration: int
) -> tuple[list[TrackOut], dict]:
    """Resolve mood + intensity → archive.org tracks. Falls back to a deterministic
    pool if archive.org returns nothing so the UI is never left empty."""
    mood_cfg = MOOD_INTENSITY_MAP.get(mood_name)
    if mood_cfg is None:
        raise _validation_error(
            f"unknown currentMood '{mood_name}'. Allowed: {list(MOOD_INTENSITY_MAP.keys())}"
        )
    bucket = get_intensity_range(intensity)
    context = mood_cfg[bucket]
    search_query = context["searchQuery"]
    target_tags = list(context["targetTags"])

    # ~6 minutes per ambient track on average — round to keep playlist tight
    n = max(2, min(6, round(session_duration / 5)))

    tracks: list[WellnessTrack] = await archive_service.fetch_wellness_tracks(
        search_query, limit=n
    )
    if not tracks:
        tracks = _fallback_tracks(mood_name, intensity, n)

    return (
        [TrackOut(**t.to_dict() if isinstance(t, WellnessTrack) else t) for t in tracks],
        {"searchQuery": search_query, "targetTags": target_tags, "bucket": bucket},
    )


# Soft fallback so the UI never breaks if archive.org is unreachable
_FALLBACK_POOL = [
    {"title": "Dusk Over Still Water", "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"},
    {"title": "Slow Exhale",            "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"},
    {"title": "Cedar & Quiet",          "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3"},
    {"title": "Long Light Returning",   "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3"},
    {"title": "The Pause Between",      "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3"},
    {"title": "Soft Hands of Evening",  "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3"},
]


def _fallback_tracks(mood_name: str, intensity: int, n: int) -> list[WellnessTrack]:
    out: list[WellnessTrack] = []
    for i, t in enumerate(_FALLBACK_POOL[:n]):
        out.append(WellnessTrack(
            id=f"fb_{mood_name.lower().replace(' ', '_')}_{intensity}_{i}",
            title=t["title"],
            artist="Soundlull Reserve",
            duration=240,
            audioUrl=t["url"],
        ))
    return out


# ---------- Routes ----------

@api_router.get("/")
async def root():
    return {"message": "Soundlull Mood Wellness API"}


@api_router.get("/catalog")
async def get_catalog():
    return {"moods": MOODS, "intensities": INTENSITIES, "durations": DURATIONS}


@api_router.post("/music-wellness/generate", response_model=WellnessGenerateResponse)
async def music_wellness_generate(req: WellnessGenerateRequest):
    """Backend contract endpoint (ported from the Node/Express reference)."""
    _validate_intensity(req.intensity)
    tracks, ctx = await _generate_tracks(req.currentMood, req.intensity, req.sessionDuration)
    return WellnessGenerateResponse(
        sessionId=str(uuid.uuid4()),
        currentMood=req.currentMood,
        intensity=req.intensity,
        intensityBucket=ctx["bucket"],
        desiredMood=req.desiredMood,
        sessionDuration=req.sessionDuration,
        searchQuery=ctx["searchQuery"],
        targetTags=ctx["targetTags"],
        tracks=tracks,
    )


class PlaylistRequest(BaseModel):
    """Frontend wizard contract — keeps the existing UI working."""
    mood_id: str
    intensity_id: str
    duration_minutes: int


@api_router.post("/playlist")
async def create_playlist(req: PlaylistRequest):
    if req.mood_id not in FRONTEND_TO_BACKEND_MOOD:
        raise _validation_error(f"unknown mood_id '{req.mood_id}'")
    if req.intensity_id not in FRONTEND_INTENSITY_TO_NUMBER:
        raise _validation_error(f"unknown intensity_id '{req.intensity_id}'")
    if req.duration_minutes not in DURATIONS:
        raise _validation_error(f"duration_minutes must be one of {DURATIONS}")

    mood_name = FRONTEND_TO_BACKEND_MOOD[req.mood_id]
    intensity_num = FRONTEND_INTENSITY_TO_NUMBER[req.intensity_id]

    tracks, ctx = await _generate_tracks(mood_name, intensity_num, req.duration_minutes)
    return {
        "session_id": str(uuid.uuid4()),
        "mood_id": req.mood_id,
        "intensity_id": req.intensity_id,
        "duration_minutes": req.duration_minutes,
        "search_query": ctx["searchQuery"],
        "target_tags": ctx["targetTags"],
        # tracks expose both `url` (legacy frontend) and `audioUrl` (new contract)
        "tracks": [
            {
                "id": t.id,
                "title": t.title,
                "artist": t.artist,
                "duration": t.duration,
                "url": t.audioUrl,
                "audioUrl": t.audioUrl,
            }
            for t in tracks
        ],
    }


# Translate our HTTPException(detail=dict) into the {error, message} envelope
# expected by the Node test contract.
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

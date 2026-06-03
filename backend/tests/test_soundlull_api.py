"""Backend tests for Soundlull endpoints.

Covers:
- GET /api/catalog (wizard data)
- POST /api/playlist (legacy frontend wizard contract)
- POST /api/music-wellness/generate (new Node-parity contract)
"""
import os
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
HTTP_TIMEOUT = 30  # archive.org first call can be slow


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- /api/catalog ----------

class TestCatalog:
    def test_catalog_returns_200_and_counts(self, session):
        r = session.get(f"{API}/catalog", timeout=HTTP_TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["moods"]) == 5
        assert len(data["intensities"]) == 5
        assert data["durations"] == [5, 10, 15, 20, 30]
        mood_ids = {m["id"] for m in data["moods"]}
        assert {"stressed", "unfocused", "low_energy", "anxious", "restless"} == mood_ids
        intensity_ids = {i["id"] for i in data["intensities"]}
        assert "balanced" in intensity_ids


# ---------- /api/music-wellness/generate (new Node contract) ----------

class TestMusicWellnessGenerate:
    URL = None  # set per call

    def _post(self, session, payload):
        return session.post(f"{API}/music-wellness/generate", json=payload, timeout=HTTP_TIMEOUT)

    def test_intensity_42_returns_validation_error(self, session):
        r = self._post(session, {"currentMood": "Anxious", "intensity": 42})
        assert r.status_code == 400, r.text
        body = r.json()
        assert body["error"] == "ValidationError"
        assert isinstance(body.get("message"), str)
        # Must be exactly {"error", "message"} envelope (no "detail")
        assert set(body.keys()) == {"error", "message"}

    def test_intensity_0_returns_validation_error(self, session):
        r = self._post(session, {"currentMood": "Anxious", "intensity": 0})
        assert r.status_code == 400
        assert r.json()["error"] == "ValidationError"

    def test_intensity_6_returns_validation_error(self, session):
        r = self._post(session, {"currentMood": "Anxious", "intensity": 6})
        assert r.status_code == 400
        assert r.json()["error"] == "ValidationError"

    def test_unknown_current_mood_returns_validation_error(self, session):
        r = self._post(session, {"currentMood": "Joyful", "intensity": 3})
        assert r.status_code == 400
        body = r.json()
        assert body["error"] == "ValidationError"

    def test_happy_path_anxious_intensity_4(self, session):
        payload = {
            "currentMood": "Anxious",
            "intensity": 4,
            "desiredMood": "Calm",
            "musicPreferences": ["Piano"],
            "sessionDuration": 15,
        }
        r = self._post(session, payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("sessionId"), str) and len(data["sessionId"]) > 0
        assert data["intensityBucket"] == "high"
        assert data["searchQuery"] == "meditation ambient"
        assert "healing" in data["targetTags"]
        assert data["currentMood"] == "Anxious"
        assert data["desiredMood"] == "Calm"
        assert data["sessionDuration"] == 15
        assert isinstance(data["tracks"], list) and len(data["tracks"]) > 0
        for t in data["tracks"]:
            assert "id" in t and isinstance(t["id"], str)
            assert "title" in t and isinstance(t["title"], str)
            assert "artist" in t and isinstance(t["artist"], str)
            assert "duration" in t and isinstance(t["duration"], int)
            assert "audioUrl" in t and isinstance(t["audioUrl"], str)
            assert (
                t["audioUrl"].startswith("https://archive.org/download/")
                or t["audioUrl"].startswith("https://www.soundhelix.com/")
            ), f"Unexpected audioUrl: {t['audioUrl']}"

    def test_intensity_1_bucket_low(self, session):
        r = self._post(session, {"currentMood": "Anxious", "intensity": 1})
        assert r.status_code == 200, r.text
        assert r.json()["intensityBucket"] == "low"

    def test_intensity_2_bucket_low(self, session):
        r = self._post(session, {"currentMood": "Anxious", "intensity": 2})
        assert r.status_code == 200, r.text
        assert r.json()["intensityBucket"] == "low"

    def test_intensity_3_bucket_high(self, session):
        r = self._post(session, {"currentMood": "Anxious", "intensity": 3})
        assert r.status_code == 200, r.text
        assert r.json()["intensityBucket"] == "high"


# ---------- /api/playlist (legacy frontend wizard) ----------

class TestPlaylist:
    def _post(self, session, payload):
        return session.post(f"{API}/playlist", json=payload, timeout=HTTP_TIMEOUT)

    def test_playlist_valid_request(self, session):
        payload = {"mood_id": "stressed", "intensity_id": "balanced", "duration_minutes": 10}
        r = self._post(session, payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mood_id"] == "stressed"
        assert data["intensity_id"] == "balanced"
        assert data["duration_minutes"] == 10
        assert isinstance(data["session_id"], str) and len(data["session_id"]) > 0
        assert "search_query" in data and isinstance(data["search_query"], str)
        assert "target_tags" in data and isinstance(data["target_tags"], list)
        assert isinstance(data["tracks"], list) and len(data["tracks"]) > 0
        for t in data["tracks"]:
            # legacy + new contract fields present
            assert "id" in t and "title" in t and "artist" in t and "duration" in t
            assert "url" in t and "audioUrl" in t
            assert t["url"] == t["audioUrl"]
            assert (
                t["url"].startswith("https://archive.org/download/")
                or t["url"].startswith("https://www.soundhelix.com/")
            ), f"Unexpected url: {t['url']}"

    def test_invalid_mood(self, session):
        r = self._post(session, {"mood_id": "happy", "intensity_id": "balanced", "duration_minutes": 10})
        assert r.status_code == 400
        assert r.json()["error"] == "ValidationError"

    def test_invalid_intensity(self, session):
        r = self._post(session, {"mood_id": "stressed", "intensity_id": "wild", "duration_minutes": 10})
        assert r.status_code == 400
        assert r.json()["error"] == "ValidationError"

    def test_invalid_duration(self, session):
        r = self._post(session, {"mood_id": "stressed", "intensity_id": "balanced", "duration_minutes": 7})
        assert r.status_code == 400
        assert r.json()["error"] == "ValidationError"


# ---------- helper utility parity tests (parse_length_to_seconds) ----------

class TestParseLengthHelper:
    """Direct import test for the Node-ported helper."""

    def test_mm_ss(self):
        from audio_archive_service import parse_length_to_seconds
        assert parse_length_to_seconds("04:15") == 255

    def test_float_seconds(self):
        from audio_archive_service import parse_length_to_seconds
        assert parse_length_to_seconds("242.00") == 242

    def test_empty_uses_fallback(self):
        from audio_archive_service import parse_length_to_seconds
        assert parse_length_to_seconds("") == 180

    def test_none_uses_fallback(self):
        from audio_archive_service import parse_length_to_seconds
        assert parse_length_to_seconds(None) == 180

    def test_hh_mm_ss(self):
        from audio_archive_service import parse_length_to_seconds
        assert parse_length_to_seconds("01:02:03") == 3723

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


# ---------- PlaylistBuilder (Node parity contract) ----------

class TestPlaylistBuilder:
    """Direct unit tests for the ported playlist scoring/assembly logic."""

    def test_score_track_exact_85_contract(self):
        from playlist_builder import PlaylistBuilder
        from audio_archive_service import WellnessTrack

        track = WellnessTrack(
            id="archive_track_01",
            title="Deep Ambient Meditation Bliss",
            artist="Wellness Producer",
            duration=300,
            audioUrl="https://archive.org/download/x/x.mp3",
        )
        # subject 'meditation' is in target_tags (+30); 'calm' is not (+0)
        # 'meditation' in title (+15), 'ambient' in title (+15)
        # user pref 'Ambient' substring in title (+25) → total 85
        score = PlaylistBuilder.score_track(
            track,
            subjects=["meditation", "calm"],
            target_tags=["meditation", "ambient"],
            user_preferences=["Ambient"],
        )
        assert score == 85

    def test_score_track_camelcase_alias_works(self):
        from playlist_builder import PlaylistBuilder
        from audio_archive_service import WellnessTrack

        track = WellnessTrack("id1", "Deep Ambient Meditation Bliss", "x", 300, "u")
        score_snake = PlaylistBuilder.score_track(
            track, ["meditation", "calm"], ["meditation", "ambient"], ["Ambient"]
        )
        score_camel = PlaylistBuilder.scoreTrack(
            track, ["meditation", "calm"], ["meditation", "ambient"], ["Ambient"]
        )
        assert score_snake == score_camel == 85

    def test_build_session_playlist_picks_highest_within_budget(self):
        from playlist_builder import PlaylistBuilder
        from audio_archive_service import WellnessTrack

        # Contract pool: 1 highly-scoring 300s track + 1 unrelated 180s clip
        mock_item = WellnessTrack(
            id="archive_track_01",
            title="Deep Ambient Meditation Bliss",
            artist="Wellness Producer",
            duration=300,
            audioUrl="https://archive.org/download/x/x.mp3",
        )
        short_clip = WellnessTrack(
            id="short_clip",
            title="Relax Short",
            artist="Other",
            duration=180,
            audioUrl="https://archive.org/download/y/y.mp3",
        )
        raw_pool = [
            {"doc": mock_item, "subjects": ["meditation"]},
            {"doc": short_clip, "subjects": ["relax"]},
        ]
        # session_minutes=5 → 300s budget. highest-scoring track (300s) fits exactly,
        # consumes whole budget → only 1 track in output
        out = PlaylistBuilder.build_session_playlist(
            raw_pool,
            session_minutes=5,
            target_tags=["meditation"],
            user_preferences=["Ambient"],
        )
        assert len(out) == 1
        assert out[0].id == "archive_track_01"

    def test_build_session_playlist_camelcase_alias(self):
        from playlist_builder import PlaylistBuilder
        from audio_archive_service import WellnessTrack

        item = WellnessTrack("archive_track_01", "Deep Ambient Meditation Bliss", "x", 300, "u")
        raw_pool = [{"doc": item, "subjects": ["meditation"]}]
        out = PlaylistBuilder.buildSessionPlaylist(
            raw_pool, 5, ["meditation"], ["Ambient"]
        )
        assert len(out) == 1 and out[0].id == "archive_track_01"

    def test_score_track_no_matches_returns_zero(self):
        from playlist_builder import PlaylistBuilder
        from audio_archive_service import WellnessTrack

        track = WellnessTrack("id1", "Jazz Piano Trio", "x", 200, "u")
        assert PlaylistBuilder.score_track(track, ["loud"], ["sleep"], ["Drone"]) == 0

    def test_build_session_playlist_skips_oversize_track(self):
        from playlist_builder import PlaylistBuilder
        from audio_archive_service import WellnessTrack

        big = WellnessTrack("big", "Ambient Meditation Drone", "x", 1000, "u")
        small = WellnessTrack("small", "Ambient Meditation Light", "x", 120, "u")
        raw_pool = [
            {"doc": big, "subjects": ["meditation"]},
            {"doc": small, "subjects": ["meditation"]},
        ]
        # 3 min budget = 180s. Big (1000s) skipped; small (120s) fits.
        out = PlaylistBuilder.build_session_playlist(
            raw_pool, 3, ["meditation"], []
        )
        assert [t.id for t in out] == ["small"]


# ---------- Integration: musicPreferences flows through generate ----------

class TestMusicPreferencesPipeline:
    def test_generate_respects_session_duration_budget(self, session):
        """Sum of returned durations should fit session budget (allow safety-net of top-2 from pool)."""
        payload = {
            "currentMood": "Anxious",
            "intensity": 4,
            "musicPreferences": ["Ambient"],
            "sessionDuration": 10,
        }
        r = session.post(f"{API}/music-wellness/generate", json=payload, timeout=HTTP_TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        budget_sec = data["sessionDuration"] * 60
        total = sum(t["duration"] for t in data["tracks"])
        # Allow generous tolerance: if pool tracks all exceed budget, server falls back
        # to top-2 scored tracks (which may exceed the budget). Otherwise must fit.
        assert len(data["tracks"]) > 0
        if len(data["tracks"]) > 2:
            assert total <= budget_sec, (
                f"Greedy assembly exceeded budget: {total}s > {budget_sec}s"
            )

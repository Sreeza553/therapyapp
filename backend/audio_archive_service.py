"""Internet Archive (archive.org) wellness track fetcher.

Ported from the Node/TypeScript reference: src/services/audioArchiveService.ts.

Two-step pipeline:
  1. advancedsearch.php → list of candidate item identifiers
  2. metadata/{id}/files → filter MP3 assets per item

Includes:
  - parse_length_to_seconds: '04:15' → 255, '242.00' → 242, '' → 180 (fallback)
  - fetch_wellness_tracks(query, limit): returns List[WellnessTrack]
  - In-memory TTL cache to avoid hammering archive.org
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, asdict
from typing import Optional

import httpx

log = logging.getLogger(__name__)

ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA_URL = "https://archive.org/metadata"
ARCHIVE_DOWNLOAD_URL = "https://archive.org/download"

DEFAULT_FALLBACK_SECONDS = 180
HTTP_TIMEOUT = 10.0
CACHE_TTL_SECONDS = 60 * 30  # 30 minutes


@dataclass
class WellnessTrack:
    id: str
    title: str
    artist: str
    duration: int  # seconds
    audioUrl: str  # camelCase to match TypeScript contract

    def to_dict(self) -> dict:
        return asdict(self)


def parse_length_to_seconds(length: Optional[str]) -> int:
    """Normalize archive.org's varied length formats to integer seconds.

    Examples:
        '04:15'  → 255   (mm:ss)
        '01:02:03' → 3723 (hh:mm:ss)
        '242.00' → 242   (float seconds)
        ''       → 180   (fallback)
        None     → 180
    """
    if not length:
        return DEFAULT_FALLBACK_SECONDS
    s = str(length).strip()
    if not s:
        return DEFAULT_FALLBACK_SECONDS
    if ":" in s:
        parts = s.split(":")
        try:
            nums = [int(float(p)) for p in parts]
        except (ValueError, TypeError):
            return DEFAULT_FALLBACK_SECONDS
        total = 0
        for n in nums:
            total = total * 60 + n
        return total
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return DEFAULT_FALLBACK_SECONDS


class _Cache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, list[WellnessTrack]]] = {}

    def get(self, key: str) -> Optional[list[WellnessTrack]]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, tracks = entry
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return tracks

    def set(self, key: str, tracks: list[WellnessTrack]) -> None:
        self._store[key] = (time.time() + CACHE_TTL_SECONDS, tracks)


class AudioArchiveService:
    def __init__(self) -> None:
        self._cache = _Cache()

    # exposed for tests/parity with the Node contract
    parse_length_to_seconds = staticmethod(parse_length_to_seconds)

    @staticmethod
    def _build_search_params(query: str, rows: int) -> dict:
        # Restrict to streaming audio in CC / public-domain collections
        scoped_q = (
            f'({query}) AND mediatype:(audio) AND '
            'collection:(opensource_audio OR audio_music OR netlabels)'
        )
        return {
            "q": scoped_q,
            "fl[]": ["identifier", "title", "creator", "runtime", "subject"],
            "rows": rows,
            "page": 1,
            "output": "json",
            "sort[]": "downloads desc",
        }

    @staticmethod
    def _pick_best_mp3(files: list[dict]) -> Optional[dict]:
        """Prefer high-quality 'VBR MP3' over derived '64Kbps MP3'."""
        if not files:
            return None
        mp3s = [f for f in files if str(f.get("format", "")).lower().endswith("mp3") or
                str(f.get("name", "")).lower().endswith(".mp3")]
        if not mp3s:
            return None
        for fmt in ("VBR MP3", "MP3", "64Kbps MP3"):
            for f in mp3s:
                if str(f.get("format", "")).lower() == fmt.lower():
                    return f
        return mp3s[0]

    async def fetch_wellness_tracks(
        self, query: str, limit: int = 6
    ) -> list[WellnessTrack]:
        pool = await self.fetch_wellness_pool(query, limit=limit)
        return [item["doc"] for item in pool]

    async def fetch_wellness_pool(
        self, query: str, limit: int = 15
    ) -> list[dict]:
        """Fetch a scoring-ready pool: list of {'doc': WellnessTrack, 'subjects': [str]}."""
        cache_key = hashlib.md5(f"pool|{query}|{limit}".encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached:
            log.info("audio-archive pool cache hit: %s", query)
            return cached  # type: ignore[return-value]

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            # Step 1 — advanced search
            try:
                resp = await client.get(
                    ARCHIVE_SEARCH_URL,
                    params=self._build_search_params(query, rows=max(limit * 2, 20)),
                )
                resp.raise_for_status()
                docs = (resp.json() or {}).get("response", {}).get("docs", []) or []
            except Exception as e:
                log.warning("archive.org search failed for '%s': %s", query, e)
                return []

            async def hydrate(doc: dict) -> dict | None:
                ident = doc.get("identifier")
                if not ident:
                    return None
                try:
                    files_resp = await client.get(f"{ARCHIVE_METADATA_URL}/{ident}/files")
                    files_resp.raise_for_status()
                    payload = files_resp.json() or {}
                    files = payload.get("result") or payload.get("files") or []
                except Exception as e:
                    log.debug("metadata fetch failed for %s: %s", ident, e)
                    return None

                file_obj = self._pick_best_mp3(files)
                if not file_obj:
                    return None  # gracefully skip buckets with no MP3

                title = doc.get("title") or file_obj.get("title") or ident
                creator = doc.get("creator")
                if isinstance(creator, list):
                    creator = ", ".join(str(c) for c in creator) if creator else None
                artist = creator or file_obj.get("creator") or "Internet Archive"

                length_str = file_obj.get("length") or doc.get("runtime") or ""
                duration = parse_length_to_seconds(length_str)

                subj = doc.get("subject")
                if isinstance(subj, str):
                    subjects = [s.strip() for s in subj.split(";") if s.strip()]
                elif isinstance(subj, list):
                    subjects = [str(s).strip() for s in subj if str(s).strip()]
                else:
                    subjects = []

                audio_url = f"{ARCHIVE_DOWNLOAD_URL}/{ident}/{file_obj.get('name')}"
                track = WellnessTrack(
                    id=f"ia_{ident}",
                    title=str(title)[:120],
                    artist=str(artist)[:80],
                    duration=duration,
                    audioUrl=audio_url,
                )
                return {"doc": track, "subjects": subjects}

            results = await asyncio.gather(*(hydrate(d) for d in docs[: max(limit * 2, 20)]))
            pool = [r for r in results if r is not None][:limit]

        if pool:
            self._cache.set(cache_key, pool)  # type: ignore[arg-type]
        return pool


# Module-level singleton
archive_service = AudioArchiveService()

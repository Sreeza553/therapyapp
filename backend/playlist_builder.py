"""PlaylistBuilder — score and assemble wellness tracks within a session budget.

Ported from the Node/TypeScript reference: src/utils/playlistBuilder.ts.

Scoring rules:
  +30 per subject term that also appears in target_tags (case-insensitive)
  +15 per target_tag substring found in the track title (case-insensitive)
  +25 per user preference (genre) substring found in the track title

Assembly:
  Sort tracks by score descending, greedily pack into the session budget
  (session_minutes * 60 seconds). Skip tracks that exceed the remaining budget.
"""

from __future__ import annotations

from typing import Iterable


def _to_lower_set(values: Iterable) -> set[str]:
    return {str(v).lower() for v in (values or [])}


def score_track(
    track,
    subjects: Iterable,
    target_tags: Iterable,
    user_preferences: Iterable,
) -> int:
    """Compute an integer score for a track per the contract.

    `track` is anything with a `.title` attribute (WellnessTrack or duck-typed).
    """
    title_lower = (getattr(track, "title", "") or "").lower()
    target_lower = _to_lower_set(target_tags)

    score = 0
    # +30 per matching subject that is also a target tag
    for s in subjects or []:
        if str(s).lower() in target_lower:
            score += 30
    # +15 per target tag substring present in the title
    for t in target_tags or []:
        if str(t).lower() in title_lower:
            score += 15
    # +25 per user-preference substring present in the title
    for p in user_preferences or []:
        if str(p).lower() in title_lower:
            score += 25
    return score


def build_session_playlist(
    raw_pool: list[dict],
    session_minutes: int,
    target_tags: Iterable,
    user_preferences: Iterable,
) -> list:
    """Greedy, score-first assembly. Each pool item is {'doc': track, 'subjects': [...]}."""
    budget_sec = int(session_minutes) * 60

    scored: list[tuple[int, object]] = []
    for item in raw_pool or []:
        doc = item.get("doc")
        if doc is None:
            continue
        subjects = item.get("subjects", [])
        scored.append((score_track(doc, subjects, target_tags, user_preferences), doc))

    scored.sort(key=lambda entry: entry[0], reverse=True)

    playlist: list = []
    remaining = budget_sec
    for _, doc in scored:
        dur = int(getattr(doc, "duration", 0) or 0)
        if dur <= remaining:
            playlist.append(doc)
            remaining -= dur
        if remaining <= 0:
            break
    return playlist


class PlaylistBuilder:
    """Static facade matching the Node `PlaylistBuilder.scoreTrack(...)` syntax."""

    scoreTrack = staticmethod(score_track)
    score_track = staticmethod(score_track)
    buildSessionPlaylist = staticmethod(build_session_playlist)
    build_session_playlist = staticmethod(build_session_playlist)

"""Mood → intensity bucket → archive.org search hint mappings.

Ported from the Node/TypeScript reference: src/data/moodMappings.ts.
- getIntensityRange(n): 1–2 → 'low', 3–5 → 'high'
- MOOD_INTENSITY_MAP[mood][bucket] = { searchQuery, targetTags }
"""

from typing import Literal

IntensityBucket = Literal["low", "high"]


def get_intensity_range(intensity: int) -> IntensityBucket:
    if intensity <= 2:
        return "low"
    return "high"


# Search hints for the Internet Archive. Each mood × bucket has a tuned query
# and a list of preferred tags used to score/sort candidate tracks.
MOOD_INTENSITY_MAP: dict[str, dict[str, dict]] = {
    "Anxious": {
        "low":  {"searchQuery": "ambient calm",         "targetTags": ["meditation", "healing", "soft"]},
        "high": {"searchQuery": "meditation ambient",   "targetTags": ["healing", "relaxation", "calm"]},
    },
    "Stressed": {
        "low":  {"searchQuery": "ambient piano gentle", "targetTags": ["piano", "soft", "ambient"]},
        "high": {"searchQuery": "deep relaxation drone","targetTags": ["drone", "healing", "deep"]},
    },
    "Restless": {
        "low":  {"searchQuery": "ambient nature sleep", "targetTags": ["sleep", "nature", "soft"]},
        "high": {"searchQuery": "binaural sleep ambient","targetTags": ["sleep", "binaural", "deep"]},
    },
    "Unfocused": {
        "low":  {"searchQuery": "ambient focus instrumental","targetTags": ["focus", "ambient", "instrumental"]},
        "high": {"searchQuery": "lofi study instrumental",   "targetTags": ["focus", "lofi", "study"]},
    },
    "Low Energy": {
        "low":  {"searchQuery": "uplifting acoustic instrumental","targetTags": ["uplifting", "warm", "acoustic"]},
        "high": {"searchQuery": "warm orchestral instrumental",  "targetTags": ["uplifting", "warm", "orchestral"]},
    },
    "Calm": {
        "low":  {"searchQuery": "ambient gentle instrumental","targetTags": ["calm", "ambient"]},
        "high": {"searchQuery": "soundscape relaxation",     "targetTags": ["soundscape", "relaxation"]},
    },
}

# Friendly map: frontend uses snake_case ids; backend test contract uses CapCase labels.
FRONTEND_TO_BACKEND_MOOD = {
    "anxious":    "Anxious",
    "stressed":   "Stressed",
    "restless":   "Restless",
    "unfocused":  "Unfocused",
    "low_energy": "Low Energy",
}

# Intensity slider id → numeric (1–5) used by the backend contract
FRONTEND_INTENSITY_TO_NUMBER = {
    "gentle":    1,
    "mild":      2,
    "balanced":  3,
    "deep":      4,
    "immersive": 5,
}

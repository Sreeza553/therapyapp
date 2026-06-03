# Soundlull — Mood Wellness Audio Therapy

## Original Problem Statement
Build a frontend-first Mood Wellness Audio Therapy app with a 3-step wizard (Mood → Intensity → Duration), a calming loading transition, an audio therapy player, a post-session feedback check-in, and a completion screen. UI must feel intuitive, calming, intentional, and work for elders, millennials, and Gen Z.

## User Choices (confirmed)
- Audio source: royalty-free demo URLs (SoundHelix)
- Backend logic: pre-curated, deterministic static playlists
- Auth: none (anonymous, session-only)
- Theme: soft pastel calm (sage, cream, dusty rose)
- Feedback screen: full interactive UI but frontend-only (no DB persistence)

## Architecture
- **Backend**: FastAPI (`/app/backend/server.py`)
  - `GET /api/catalog` → moods, intensities, durations
  - `POST /api/playlist` → deterministic curated playlist (seeded by mood+intensity+duration)
- **Frontend**: React + Tailwind + Framer Motion
  - Wizard state machine in `pages/Soundlull.jsx`
  - Modular components in `components/wellness/`
  - Custom palette + breathing animations in `tailwind.config.js` / `index.css`
  - Fonts: Cormorant Garamond (headings) + Outfit (body)

## Implemented (Feb 2026)
- Welcome screen with cinematic hero (lush imagery + aurora orb glow)
- Mood selector — 5 image-backed glass cards with calming labels
- Intensity selector — 5 luminescent glass cards with depth meter
- Duration selector — 5/10/15/20/30 minutes with glowing gold-select state
- Calming loading transition (multi-color breathing orbs + "Curating your peace…")
- Audio player — dark cinematic, glowing breathing visualizer, play/pause/skip/prev, gold progress bar, glass queue + session meta
- Feedback screen — glass cards with "How are you feeling now?" 5 options
- Completion screen with aurora glow and restart CTA
- Wizard progress indicator with gold accent across all steps
- Aurora-mesh ambient backdrop + grain noise overlay
- Internet Archive (archive.org) audio integration — real public-domain ambient music
- Backend API contract ported from Node/Express to Python FastAPI:
  - `POST /api/music-wellness/generate` (Node test contract) — validation envelope `{error: 'ValidationError', message}`, intensityBucket logic (1-2→low, 3-5→high), search queries + tags per mood, `musicPreferences[]` flow into scoring
  - `POST /api/playlist` (frontend wizard) — exposes both `url` and `audioUrl` for compatibility
  - `GET /api/catalog` — moods/intensities/durations metadata
- `PlaylistBuilder` ported from Node `src/utils/playlistBuilder.ts`:
  - `score_track / scoreTrack`: +30 per subject ∈ targetTags, +15 per targetTag in title, +25 per user-pref in title (case-insensitive)
  - `build_session_playlist / buildSessionPlaylist`: greedy score-first pack into `session_minutes * 60` budget
  - Safety net: if budget excludes all candidates, fall back to top-2 highest-scored tracks
- 30-min in-memory cache (non-empty results only) + SoundHelix fallback if archive.org is unreachable
- Full data-testid coverage

## User Personas
- Elders — large touch targets (≥48px), high contrast, generous spacing
- Millennials — editorial typography, soft palette, modern wellness aesthetic
- Gen Z — micro-animations, asymmetric layouts, distinctive font pairing

## Backlog (P1 / P2)
- P1: Persist session history (requires auth or anonymous session id)
- P1: Real curated royalty-free wellness audio (replace SoundHelix demo tracks)
- P1: Breathing-guide overlay synced to track (inhale/hold/exhale prompts)
- P2: Share completion card image (generate downloadable PNG)
- P2: Daily streak / gentle reminders (requires auth)
- P2: Custom session length input (slider beyond preset 5–30 min)
- P2: Spotify / Apple Music integration for users with paid accounts

## Test Coverage
- Backend: 100% (6/6) — catalog counts, happy path, determinism, 400s for invalid input
- Frontend: 100% happy path — full wizard, player controls, feedback, completion, restart
- Tests: `/app/backend/tests/test_soundlull_api.py`

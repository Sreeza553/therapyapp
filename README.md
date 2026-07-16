
# Soundlull Mood Wellness App

Soundlull is a wellness-focused music therapy experience that helps users choose a mood, intensity, and session duration to generate a calming playlist. The project is split into a TypeScript Express backend and a React frontend.

## Project Overview

- Frontend: React + CRA + Tailwind-based UI for the guided wellness flow
- Backend: Express + TypeScript API that serves catalog data and playlist generation
- Goal: provide a simple, soothing session builder for mood-based audio therapy

## Repository Structure

- `backend/` — Express API and TypeScript service logic
- `frontend/` — React app for the user experience
- `memory/` — product requirements and planning artifacts
- `test_reports/` — test output summaries

## Prerequisites

Before you begin, make sure you have:

- Node.js 18+ or newer
- npm or yarn
- A modern browser

## Quick Start

### 1. Install backend dependencies

From the `backend/` directory:

```bash
npm install
```

### 2. Start the backend

```bash
npm run dev
```

The API will run at:

- http://localhost:8000

### 3. Install frontend dependencies

From the `frontend/` directory:

```bash
npm install
```

### 4. Configure the frontend environment

Create a `.env` file inside `frontend/` with:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

### 5. Start the frontend

```bash
npm start
```

The app will open in your browser at:

- http://localhost:3000

## Backend API

The backend exposes the following main routes:

- `GET /api/` — health/info route
- `GET /api/catalog` — returns mood, intensity, and duration options
- `POST /api/playlist` — creates a playlist for the selected mood/intensity/duration

### Example payload for playlist generation

```json
{
  "mood_id": "stressed",
  "intensity_id": "gentle",
  "duration_minutes": 10
}
```

## Frontend Behavior

The React app guides a user through:

1. Welcome screen
2. Mood selection
3. Intensity selection
4. Duration selection
5. Playlist playback and reflection flow

## Testing

### Backend tests

From `backend/`:

```bash
npm test
```

### Frontend tests

From `frontend/`:

```bash
npm test -- --watch=false
```

## Production Build

### Backend build

```bash
cd backend
npm run build
```

### Frontend production build

```bash
cd frontend
npm run build
```

## Notes

- The backend is configured to accept CORS requests from the frontend by default.
- If you deploy the frontend to a different domain, update `REACT_APP_BACKEND_URL` to point to the deployed backend.
- For local development, keep the backend and frontend running in separate terminals.

## Troubleshooting

If the frontend cannot load the session catalog:

- confirm the backend is running on port `8000`
- verify the `.env` file in `frontend/` contains the correct `REACT_APP_BACKEND_URL`
- check the browser console for connection errors

If the backend fails to start:

- verify dependencies were installed with `npm install`
- ensure Node.js version is compatible
- review the TypeScript/Express startup logs for missing modules or environment issues
=======



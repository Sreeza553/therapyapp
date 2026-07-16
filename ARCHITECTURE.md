# Architecture and Workflow Guide

This document explains the project in simple terms so someone new to the codebase can understand how it works.

## 1. What this project is doing

This application helps a user create a calming audio session based on their current mood, preferred intensity, and session duration.

In simple terms:

1. The user selects a mood such as stressed or anxious.
2. The user chooses how strong the session should feel.
3. The app asks how long the session should last.
4. The backend generates a playlist of music/audio suggestions.
5. The frontend plays those tracks and guides the user through the experience.

---

## 2. High-level architecture

The project is split into two main parts:

- Frontend: the user interface that the user sees and interacts with
- Backend: the API that provides the playlist data and catalog information

A simple mental model is:

- The frontend asks questions and displays screens.
- The backend handles the logic for generating music recommendations.
- The frontend calls the backend through HTTP requests.

### Basic flow

```text
User browser
   ↓
React frontend
   ↓
HTTP request to backend API
   ↓
Express + TypeScript backend
   ↓
Playlist generation logic
   ↓
Tracks returned to frontend
   ↓
Audio session is played to the user
```

---

## 3. Frontend architecture

The frontend lives in the `frontend/` folder and is built using React.

### Main responsibility

The frontend is responsible for:

- showing the guided wellness screens
- collecting user input
- sending requests to the backend
- playing the returned tracks
- showing progress and reflection screens

### Important frontend files

- `frontend/src/App.js` — the main app entry point
- `frontend/src/pages/Soundlull.jsx` — the main workflow page that controls the whole user journey
- `frontend/src/components/wellness/` — all the step-by-step screens and UI pieces

### How the frontend works

The main page in `Soundlull.jsx` uses React state to track the current step in the user journey:

- welcome
- mood selection
- intensity selection
- duration selection
- loading
- session playback
- reflection
- completion

The page keeps values like:

- `moodId`
- `intensityId`
- `duration`
- `playlist`
- `error`

These values are updated as the user moves through the experience.

### Frontend request flow

When a user completes the selection steps, the frontend makes a request to the backend:

- `GET /api/catalog` to fetch available moods, intensities, and durations
- `POST /api/playlist` to request a session playlist

The frontend receives a JSON response and turns that into the actual UI content and audio playback experience.

---

## 4. Backend architecture

The backend lives in the `backend/` folder and is built with Express and TypeScript.

### Main responsibility

The backend is responsible for:

- exposing API endpoints
- receiving requests from the frontend
- validating input
- generating playlist suggestions
- returning a structured response to the frontend

### Important backend files

- `backend/src/index.ts` — main server entry point
- `backend/src/data/moodMappings.ts` — mood-to-search mapping
- `backend/src/services/audioArchiveService.ts` — service that fetches wellness-related audio candidates
- `backend/src/utils/playlistBuilder.ts` — logic that selects the best tracks for the session

### Backend structure

The backend creates an Express app and uses a router mounted at `/api`.

The main routes are:

- `GET /api/` — simple API welcome message
- `GET /api/catalog` — returns available choices for the UI
- `POST /api/playlist` — creates a playlist based on user selections

### What happens inside the playlist endpoint

When the frontend sends a `POST /api/playlist` request, the backend does the following:

1. Reads the request body values:
   - mood ID
   - intensity ID
   - duration
2. Validates the values.
3. Maps the provided mood and intensity into backend-friendly values.
4. Uses the mood mapping and playlist builder to prepare a list of tracks.
5. Returns the selected tracks as JSON.

---

## 5. Why the architecture is split this way

This project separates the responsibilities clearly:

- The frontend handles interface and user interaction.
- The backend handles data and music session generation.
- The API is the connection point between the two.

This makes the code easier to understand and easier to extend.

For example:

- if you want to improve the UI, you work mostly in `frontend/`
- if you want to improve the recommendation system, you work mostly in `backend/src/utils/` and `backend/src/services/`

---

## 6. End-to-end workflow

Here is the normal workflow for a user:

### Step 1: The app loads

The frontend loads the `Soundlull` page.

It immediately makes a request to:

- `GET /api/catalog`

This gives the UI the available moods, intensities, and durations.

### Step 2: The user picks a mood

The user selects something like:

- stressed
- anxious
- restless

The state in the frontend tracks the chosen mood.

### Step 3: The user chooses intensity

The user picks the strength of the session:

- gentle
- mild
- balanced
- deep
- immersive

### Step 4: The user chooses duration

The user selects how long the audio experience should run.

### Step 5: The frontend requests a playlist

The frontend sends a request to:

- `POST /api/playlist`

with the selected values.

### Step 6: The backend validates and builds the session

The backend:

- checks that the values are valid
- looks up the mood mapping
- retrieves candidate audio tracks
- uses the playlist builder to choose the best matches
- returns the results to the frontend

### Step 7: The user listens to the playlist

The frontend receives the playlist and shows the playback screen.

The user can play, pause, and move through the session as guided by the interface.

### Step 8: Reflection and completion

After the session ends, the frontend moves the user into the reflection/completion flow.

---

## 7. Main data flow in plain English

Think of the project as a pipeline:

1. The user chooses a mood and intensity.
2. The frontend passes that information to the backend.
3. The backend transforms the input into a playlist request.
4. The backend selects audio candidates.
5. The playlist response is returned to the frontend.
6. The frontend plays the audio and guides the user through the session.

---

## 8. Environment setup

The frontend expects a backend URL from the environment.

In local development, this is typically set in a `.env` file inside the frontend folder:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

This environment value tells the frontend where to send API requests.

---

## 9. Starting the app locally

### Backend

From the `backend/` directory:

```bash
npm install
npm run dev
```

This starts the Express API on:

- `http://localhost:8000`

### Frontend

From the `frontend/` directory:

```bash
npm install
npm start
```

This starts the React interface on:

- `http://localhost:3000`

---

## 10. How to read the codebase as a beginner

If you are new to this project, a good way to start is:

1. Open `frontend/src/pages/Soundlull.jsx`
   - this is where the main user journey is controlled
2. Open `backend/src/index.ts`
   - this is the main API server file
3. Open `backend/src/utils/playlistBuilder.ts`
   - this shows how the playlist is selected
4. Open `backend/src/data/moodMappings.ts`
   - this explains how moods map into search and tag logic

That order gives you a natural understanding of the project from user behavior to backend logic.

---

## 11. Summary

This project is a simple full-stack web application:

- the frontend is the guided user experience
- the backend is the playlist generation service
- the API is the bridge between them

Once you understand that one relationship, the rest of the code becomes much easier to follow.

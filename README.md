# 🌍 Wglobe

A 3D interactive weather globe — spin the Earth, search any city, and get live
weather, forecasts, air quality, UV index, news, and an AI weather assistant
(with voice) in one place.

**Live app:** https://weather-globe-six.vercel.app

## Architecture

```
┌─────────────────────┐         ┌──────────────────────────────┐
│  frontend/          │  HTTPS  │  backend/ (FastAPI)          │
│  React + Vite       │ ──────► │  deployed on Railway         │
│  Three.js globe     │         │                              │
│  deployed on Vercel │         │  ├─ OpenWeather  (live wx)   │
└─────────────────────┘         │  ├─ Open-Meteo   (UV/AQI/16d)│
                                │  ├─ GNews        (wx news)   │
        ┌───────────────┐       │  ├─ Supabase     (auth)      │
        │ AI providers  │ ◄──── │  └─ /chat  → Groq → Gemini   │
        └───────────────┘       │              → HuggingFace   │
                                └──────────────────────────────┘
```

## Features

- 🌐 **3D globe** — orbit the Earth, click/search cities, live weather popup
- 🤖 **AI assistant** — multi-provider chatbot (Groq Llama-3.3 70B → Gemini →
  HuggingFace fallback chain, 800-token replies)
- 🎤 **Voice** — ask by speaking (Web Speech API), assistant reads replies aloud
- 📅 **16-day forecast** — via Open-Meteo (3× longer than OpenWeather free tier)
- ☀️ **UV index** + safety tips, 😮‍💨 **air quality** (EU + US AQI, pollutants)
- 🕰️ **Climate history** — past-year averages, hottest/coldest/wettest days
- ⚖️ **City comparison** — side-by-side live weather for up to 6 cities
- 📰 **World weather news**, 🔐 **user accounts** (Supabase), 🗺️ weather radar

Full feature & deployment guide: [FEATURES.md](FEATURES.md)

## Repository layout

| Folder | What it is |
|---|---|
| `frontend/` | React + Vite + Three.js app (deployed on Vercel) |
| `weather-api-project/` | FastAPI backend (deployed on Railway) |

## Run locally

**Frontend**
```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173
```
The frontend talks to the production backend out of the box (`src/config.js`).

**Backend**
```bash
cd weather-api-project
pip install -r requirements.txt
copy .env.example .env        # fill in your keys
uvicorn main:app --reload --port 8000
```

## Environment variables (backend, via `.env` or Railway dashboard)

| Variable | Used for | Required |
|---|---|---|
| `GROQ_API_KEY` | Primary chatbot LLM ([console.groq.com](https://console.groq.com/keys)) | recommended |
| `GEMINI_API_KEY` | Fallback chatbot LLM ([aistudio.google.com](https://aistudio.google.com)) | recommended |
| `HUGGINGFACE_API_KEY` | Last-resort chatbot LLM ([hf.co/settings/tokens](https://huggingface.co/settings/tokens)) | optional |
| `OPENWEATHER_API_KEY` | Live weather / forecast ([openweathermap.org](https://openweathermap.org/api)) | required |
| `GNEWS_API_KEY` | Weather news ([gnews.io](https://gnews.io)) | optional |
| `SUPABASE_URL` / `SUPABASE_KEY` | Login / signup ([supabase.com](https://supabase.com)) | optional |

> ⚠️ Never commit `.env` — it is git-ignored. Open-Meteo needs **no key at all**.

## API endpoints (backend)

| Endpoint | Purpose |
|---|---|
| `GET /weather/{city}` | Live weather |
| `GET /forecast/{city}` | 5-day / 3-hour forecast |
| `GET /air-quality/{lat}/{lon}` | OpenWeather air quality |
| `GET /news` | World weather news (cached 30 min) |
| `POST /chat` | AI weather assistant (multi-provider) |
| `GET /ai-status` | Which AI providers are configured |
| `GET /openmeteo/forecast/{lat}/{lon}?days=16` | 16-day outlook |
| `GET /openmeteo/hourly/{lat}/{lon}` | Next 48 h hourly |
| `GET /openmeteo/uv/{lat}/{lon}` | UV index |
| `GET /openmeteo/air-quality/{lat}/{lon}` | EU/US AQI + pollutants |
| `GET /openmeteo/history/{lat}/{lon}` | Past-year climate stats |
| `GET /openmeteo/compare?cities=A,B,C` | Compare up to 6 cities |
| `GET /openmeteo/geocode/{name}` | City search |
| `POST /signup` · `POST /login` | Supabase auth |

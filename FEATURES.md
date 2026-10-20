# Wglobe — New Features & Deployment Guide (Oct 2026)

This document covers everything that was added to **weather-api-project** (backend) and
**weather-globe** (frontend), how to deploy it, and a roadmap of further ideas.

---

## 1. What was added

### Backend (`weather-api-project`)

| File | What it does |
|---|---|
| `ai_providers.py` (NEW) | Multi-provider AI client. Tries **Groq → Gemini → HuggingFace** in order and uses the first that responds. If one is rate-limited, the chatbot keeps working on the next. Token budget raised from 400 → **800 tokens per reply**. |
| `chat_router.py` (UPDATED) | Uses the new fallback chain. **Bug fix:** it used to call `http://localhost/weather/...` for "asked about another city" lookups, which never worked in production (Railway has no localhost app). Now it calls OpenWeather directly. History is capped at the last 10 turns so long chats don't blow the context. |
| `open_meteo.py` (NEW) | 7 new endpoints powered by **Open-Meteo** — free, no API key, no quota: |
| `main.py` (UPDATED) | Registers the Open-Meteo router + new `/ai-status` endpoint that shows which AI providers are configured. |
| `.env.example` (NEW) | Documents every environment variable. |

### New Open-Meteo endpoints (all key-free)

| Endpoint | Feature |
|---|---|
| `GET /openmeteo/geocode/{name}` | City search (returns up to 5 matches with lat/lon, country, population) |
| `GET /openmeteo/forecast/{lat}/{lon}?days=16` | **16-day daily forecast** (OpenWeather free tier only gives 5 days) |
| `GET /openmeteo/hourly/{lat}/{lon}` | Next 48 hours hourly (temp, feels-like, rain %, humidity) |
| `GET /openmeteo/uv/{lat}/{lon}` | UV index now + today's max + hourly curve |
| `GET /openmeteo/air-quality/{lat}/{lon}` | European AQI + US AQI + PM2.5/PM10/O₃/NO₂/SO₂/CO |
| `GET /openmeteo/history/{lat}/{lon}` | Past-year climate stats: averages, hottest/coldest/wettest day |
| `GET /openmeteo/compare?cities=A,B,C` | Side-by-side live weather for 2–6 cities |

### Frontend (`weather-globe`)

| File | What it does |
|---|---|
| `AIChatBox.jsx` (UPDATED) | 🎤 **Voice input** — mic button uses the browser's Web Speech API (Chrome/Edge); you speak, it transcribes and sends automatically. 🔊 **Spoken replies** — speaker toggle makes the assistant read its answers out loud (TTS). 💬 **Suggestion chips** — one-tap starter questions. |
| `WeatherExtrasPanel.jsx` / `.css` (NEW) | New "Extended Insights" panel under the 5-day forecast with three tabs: **UV Index** (live value + safety tip), **Air Quality** (EU AQI gauge + pollutant grid + advice), **16-Day** scrollable outlook with rain probability. |
| `App.jsx` (UPDATED) | Renders the new panel when a city is selected. |

Everything new is verified: the frontend passes `npm run build`, and every backend
endpoint above was smoke-tested live (200s with real data).

---

## 2. Deploy it — step by step

### Step A — Get the two new API keys (both free)

1. **Groq** (this is the big one — very generous free tier, ~6,000 tokens/min):
   - Go to <https://console.groq.com/keys> → sign in → *Create API Key* → copy it (`gsk_...`).
2. **HuggingFace** (backup provider):
   - Go to <https://huggingface.co/settings/tokens> → *New token* → type **Read** → copy it (`hf_...`).

### Step B — Add them on Railway (backend)

In the Railway dashboard (the **Variables** tab you screenshotted), add two new variables:

| Name | Value |
|---|---|
| `GROQ_API_KEY` | your `gsk_...` key |
| `HUGGINGFACE_API_KEY` | your `hf_...` key |

Keep `GEMINI_API_KEY` — it becomes the middle fallback. Railway redeploys automatically
when variables change.

Then push this updated backend code to the `gautham022/weather-api-project` GitHub repo —
Railway deploys from GitHub. (The new/changed files are listed in section 1.)

### Step C — Verify the backend

Open in a browser:

- `https://weather-api-project-production-60b8.up.railway.app/ai-status`
  → should show `{"groq": true, "gemini": true, "huggingface": true}`
- `.../openmeteo/uv/13.08/80.27` → should return a JSON with `uv_current`

### Step D — Deploy the frontend

Push the updated `weather-globe` code to GitHub; Vercel redeploys automatically.
No new environment variables needed on Vercel.

### Step E — Try it

1. Open <https://weather-globe-six.vercel.app/>, search a city.
2. In the chat: tap the **mic** and ask "will it rain tomorrow?" — the reply is sent without typing.
3. Toggle the **speaker icon** (top-right of the chat header) to hear replies spoken.
4. Under the forecast, check the new **UV / Air Quality / 16-Day** tabs.

---

## 3. AI voice agent — the LiveKit question

**Is the LiveKit voice agent possible?** Yes, but it is a *separate system*, not a
library you import into this app. `livekit/agents` is a Python framework that runs
its **own server** which joins a LiveKit room as a participant:

- You need a **LiveKit Cloud** project (free tier) or a self-hosted LiveKit server (Docker).
- The agent server itself must run **somewhere always-on** (Railway/Docker with WebSockets).
- You still need a **realtime STT-LLM-TTS stack**: e.g. Groq for the LLM + Deepgram/ElevenLabs for speech — more keys and more moving parts.
- The frontend needs `@livekit/components-react` and a token server to issue join tokens.

That is a 1–2 week project by itself and needs several more paid/free-key services.

**What was done instead (works today, zero extra keys):** the browser's built-in
**Web Speech API** — speech-to-text for your questions and text-to-speech for the
assistant's answers. It's the same tech Chrome uses for "OK Google"-style input,
works on the deployed site immediately, and costs nothing.

**If you still want LiveKit later**, the path is:
1. Create a LiveKit Cloud project → get `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`.
2. Write an agent with `pip install livekit-agents livekit-plugins-openai livekit-plugins-silero`, register a `WorkerSession` whose LLM tool calls your existing `/chat` or `/weather` endpoints.
3. Deploy it (Dockerfile) on Railway.
4. Add a "Talk to assistant" button in Wglobe that connects via `livekit-client`.

---

## 4. More feature ideas (roadmap)

**Quick wins (a few hours each):**
1. **City comparison card in the UI** — the `/openmeteo/compare` endpoint is live; add a search box "Compare weather in…" that renders a side-by-side table.
2. **Rain alert banner** — when today's `precipitation_probability_max > 60%`, show "☔ Carry an umbrella" on the popup.
3. **Sunrise/sunset widget** — already returned by OpenWeather; show a small day-light bar.
4. **Past-year climate card** — use `/openmeteo/history` for "What's Chennai usually like in October?" — great for trip planning.
5. **Language toggle** — ask the chatbot to reply in Hindi/Tamil by adding one line to the system prompt from a dropdown.

**Medium (1–3 days each):**
6. **Weather-based outfit/activity suggestions** — new `/suggest` endpoint that feeds weather + chat history into Groq with a "stylist/planner" persona.
7. **PWA (installable app)** — add a web manifest + service worker so Wglobe installs on phones and shows cached weather offline.
8. **Push/email weather digest** — daily cron on Railway sends subscribed users a morning summary (you already have Supabase users).
9. **Animated radar loop** — your WeatherRadarView can layer RainViewer's free tile API frames with a time slider.
10. **Extreme-weather warnings** — Open-Meteo + alerts formatted as toast notifications for heatwaves/storms.

**Bigger ideas:**
11. **Travel planner** — pick origin/destination/dates; the AI plans what to pack + best day to fly using the 16-day forecast + climate history.
12. **LiveKit real voice agent** (section 3) — hands-free weather assistant.
13. **Community layer** — users pin "sky reports" (photos) to the globe via Supabase storage.
14. **ML twist for the report** — train a tiny temperature-trend model on the `/openmeteo/history` archive and show "AI-predicted next week trend" vs the actual forecast.

---

## 5. File inventory (what to commit)

**weather-api-project** — changed/new:
- `ai_providers.py` (new), `open_meteo.py` (new), `.env.example` (new)
- `chat_router.py` (rewritten), `main.py` (router + `/ai-status`)

**weather-globe** — changed/new:
- `src/AIChatBox.jsx` (voice + chips), `src/AIChatBox.css` (mic/speaker/chip styles)
- `src/WeatherExtrasPanel.jsx` (new), `src/WeatherExtrasPanel.css` (new)
- `src/App.jsx` (2-line change: import + render panel)

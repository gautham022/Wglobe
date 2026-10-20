"""
chat_router.py

Weather-aware AI chat endpoint for the Wglobe backend.

Uses the multi-provider chain in ai_providers.py (Groq -> Gemini -> HuggingFace)
so the chatbot keeps working when one provider is rate-limited, with a higher
token budget than the old single-Gemini setup.
"""

import os
import re
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ai_providers import get_ai_reply, AIProviderError

router = APIRouter()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

MAX_HISTORY_TURNS = 10


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    city: Optional[str] = None
    weather: Optional[dict] = None
    history: Optional[List[ChatTurn]] = []


class ChatResponse(BaseModel):
    reply: str


CITY_PATTERN = re.compile(
    r"\b(?:in|for|at|near)\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:\?|!|\.|,|$|\s+(?:today|tomorrow|now|right now|this week))",
    re.IGNORECASE,
)


def extract_city_from_message(message: str):
    match = CITY_PATTERN.search(message)
    if match:
        return match.group(1).strip()
    return None


async def fetch_weather_for_city(city: str):
    """Call OpenWeather directly (the old localhost call never worked on Railway)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                OPENWEATHER_URL,
                params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            )
            if res.status_code == 200:
                return res.json()
    except Exception:
        pass
    return None


def build_system_prompt(city, weather, extra_city, extra_weather):
    base = (
        "You are Wglobe's AI weather assistant, built into a weather app called "
        "Wglobe. Answer questions about weather conditions, forecasts, what to "
        "wear, travel/outdoor planning, general climate/weather science questions, "
        "and related topics. Keep replies short and conversational (2-4 sentences "
        "unless more detail is asked for)."
    )
    if city and weather:
        base += f"\n\nThe user currently has {city} selected in the app. Live data: {weather}"
    if extra_city and extra_weather:
        base += f"\n\nThe user asked about {extra_city}. Live data for {extra_city}: {extra_weather}"
    elif extra_city and not extra_weather:
        base += f"\n\nThe user asked about {extra_city}, but live data could not be found for it (maybe a typo or unrecognized city name)."
    if not city and not extra_city:
        base += "\n\nNo city is currently selected, and none was mentioned in the message."
    return base


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    extra_city = extract_city_from_message(req.message)
    extra_weather = None
    if extra_city and extra_city.lower() != (req.city or "").lower():
        extra_weather = await fetch_weather_for_city(extra_city)

    system_prompt = build_system_prompt(req.city, req.weather, extra_city, extra_weather)

    turns = []
    for turn in (req.history or [])[-MAX_HISTORY_TURNS:]:
        role = "model" if turn.role == "assistant" else "user"
        turns.append({"role": role, "parts": [{"text": turn.content}]})
    turns.append({"role": "user", "parts": [{"text": req.message}]})

    try:
        reply_text = await get_ai_reply(system_prompt, turns)
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if not reply_text:
        reply_text = "Sorry, I couldn't generate a response just now."

    return ChatResponse(reply=reply_text)

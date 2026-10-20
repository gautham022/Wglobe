import os
import time
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from news import get_country_details
from supabase_client import supabase, get_supabase_client
from auth_router import router as auth_router

load_dotenv()

from chat_router import router as chat_router
from open_meteo import router as open_meteo_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://weather-globe-six.vercel.app",
        "https://weather-globe-4k4pgji1s-gautham23.vercel.app",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(open_meteo_router)


@app.get("/ai-status")
def ai_status():
    """Shows which AI providers are configured (for debugging deployments)."""
    return {
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "huggingface": bool(os.getenv("HUGGINGFACE_API_KEY")),
    }

API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

@app.get("/")
def read_root():
    return {"message": "Welcome to the Weather API"}

@app.get("/weather/{city}")
async def get_weather(city: str):
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"  # gives temperature in Celsius
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params=params)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="City not found")

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching weather data")

    data = response.json()

    return {
        "city": data["name"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "description": data["weather"][0]["description"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"],
        "wind_deg": data["wind"].get("deg", 0),
        "sunrise": data["sys"]["sunrise"],
        "sunset": data["sys"]["sunset"],
        "timezone": data["timezone"],
        "lat": data["coord"]["lat"],
        "lon": data["coord"]["lon"]
    }

FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

@app.get("/forecast/{city}")
async def get_forecast(city: str):
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(FORECAST_URL, params=params)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="City not found")

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching forecast data")

    data = response.json()

    forecast_list = []
    for entry in data["list"]:
        forecast_list.append({
            "date/time": entry["dt_txt"],
            "temperature": entry["main"]["temp"],
            "feels_like": entry["main"]["feels_like"],
            "description": entry["weather"][0]["description"],
            "humidity": entry["main"]["humidity"],
            "wind_speed": entry["wind"]["speed"]
        })

    country_code = data["city"]["country"]
    full_country_name, calling_code = await get_country_details(country_code)

    return {
        "city": data["city"]["name"],
        "country": full_country_name,
        "country_code": country_code,
        "forecast_count": len(forecast_list),
        "forecast": forecast_list
    }

AIR_QUALITY_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

@app.get("/air-quality/{lat}/{lon}")
async def get_air_quality(lat: float, lon: float):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(AIR_QUALITY_URL, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching air quality data")

    data = response.json()
    entry = data["list"][0]

    return {
        "aqi": entry["main"]["aqi"],
        "pm2_5": entry["components"]["pm2_5"],
        "pm10": entry["components"]["pm10"],
        "o3": entry["components"]["o3"]
    }

NEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NEWS_URL = "https://gnews.io/api/v4/search"

news_cache = {
    "data": None,
    "timestamp": 0
}
CACHE_DURATION_SECONDS = 30 * 60  # 30 minutes

@app.get("/news")
async def get_weather_news():
    current_time = time.time()

    if news_cache["data"] and (current_time - news_cache["timestamp"] < CACHE_DURATION_SECONDS):
        return news_cache["data"]

    params = {
        "q": "weather",
        "lang": "en",
        "max": 6,
        "apikey": NEWS_API_KEY
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(NEWS_URL, params=params)

    if response.status_code != 200:
        if news_cache["data"]:
            return news_cache["data"]
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()

    articles = []
    for item in data.get("articles", []):
        articles.append({
            "title": item["title"],
            "description": item["description"],
            "url": item["url"],
            "source": item["source"]["name"],
            "publishedAt": item["publishedAt"]
        })

    result = {"articles": articles}

    news_cache["data"] = result
    news_cache["timestamp"] = current_time

    return result

@app.get("/test-supabase")
def test_supabase():
    client = get_supabase_client()
    response = (
        client
        .table("users")
        .select("*")
        .execute()
    )

    return response.data
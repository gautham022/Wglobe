"""
open_meteo.py

Free weather features powered by Open-Meteo (https://open-meteo.com/).
Open-Meteo requires NO API key for non-commercial use, so these endpoints
never consume any of your paid/quota'd keys.

Endpoints:
  /openmeteo/geocode/{name}            - search cities by name
  /openmeteo/forecast/{lat}/{lon}      - 16-day daily forecast (OWM free = only 5 days)
  /openmeteo/hourly/{lat}/{lon}        - next 48h hourly forecast
  /openmeteo/uv/{lat}/{lon}            - UV index now + today's max
  /openmeteo/air-quality/{lat}/{lon}   - European + US AQI, pollutants
  /openmeteo/history/{lat}/{lon}       - past-year climate stats
  /openmeteo/compare?cities=A,B,C      - side-by-side city comparison
"""

import datetime as dt
import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/openmeteo")

TIMEOUT = 15.0

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

EU_AQI_LABELS = {
    0: "Good", 20: "Good", 40: "Fair", 60: "Moderate",
    80: "Poor", 100: "Very poor", 999: "Extremely poor",
}


def describe_code(code):
    return WMO_CODES.get(code, "Unknown")


def eu_aqi_label(value):
    for threshold, label in EU_AQI_LABELS.items():
        if value <= threshold:
            return label
    return "Extremely poor"


async def _get_json(url, params):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        res = await client.get(url, params=params)
    if res.status_code != 200:
        raise HTTPException(
            status_code=res.status_code,
            detail=f"Open-Meteo error: {res.text[:300]}",
        )
    return res.json()


async def geocode_city(name, count=1):
    data = await _get_json(
        GEOCODE_URL,
        {"name": name, "count": count, "language": "en", "format": "json"},
    )
    results = data.get("results", [])
    if not results:
        return None
    return [
        {
            "name": r["name"],
            "country": r.get("country"),
            "country_code": r.get("country_code"),
            "admin1": r.get("admin1"),
            "lat": r["latitude"],
            "lon": r["longitude"],
            "population": r.get("population"),
        }
        for r in results
    ]


@router.get("/geocode/{name}")
async def search_city(name: str):
    results = await geocode_city(name, count=5)
    if not results:
        raise HTTPException(status_code=404, detail="No cities found")
    return {"results": results}


@router.get("/forecast/{lat}/{lon}")
async def extended_forecast(lat: float, lon: float, days: int = Query(16, ge=1, le=16)):
    """16-day daily forecast (OpenWeather free tier only gives 5 days)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "weather_code,wind_speed_10m,surface_pressure",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,precipitation_sum,sunrise,sunset,"
                 "uv_index_max,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": days,
    }
    data = await _get_json(FORECAST_URL, params)
    daily = data["daily"]

    forecast_days = []
    for i in range(len(daily["time"])):
        forecast_days.append({
            "date": daily["time"][i],
            "description": describe_code(daily["weather_code"][i]),
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "precipitation_probability": daily["precipitation_probability_max"][i],
            "precipitation_sum": daily["precipitation_sum"][i],
            "uv_index_max": daily["uv_index_max"][i],
            "wind_speed_max": daily["wind_speed_10m_max"][i],
            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i],
        })

    current = data.get("current", {})
    return {
        "timezone": data.get("timezone"),
        "current": {
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "description": describe_code(current.get("weather_code", -1)),
            "wind_speed": current.get("wind_speed_10m"),
            "pressure": current.get("surface_pressure"),
        },
        "forecast": forecast_days,
    }


@router.get("/hourly/{lat}/{lon}")
async def hourly_forecast(lat: float, lon: float):
    """Next 48 hours, temperature + rain probability + weather description."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,apparent_temperature,weather_code,"
                  "precipitation_probability,relative_humidity_2m",
        "forecast_days": 2,
        "timezone": "auto",
    }
    data = await _get_json(FORECAST_URL, params)
    h = data["hourly"]
    hours = []
    for i in range(len(h["time"])):
        hours.append({
            "time": h["time"][i],
            "temperature": h["temperature_2m"][i],
            "feels_like": h["apparent_temperature"][i],
            "description": describe_code(h["weather_code"][i]),
            "precipitation_probability": h["precipitation_probability"][i],
            "humidity": h["relative_humidity_2m"][i],
        })
    return {"timezone": data.get("timezone"), "hourly": hours}


@router.get("/uv/{lat}/{lon}")
async def uv_index(lat: float, lon: float):
    """Current UV index (nearest hour) plus today's max and hourly curve."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "uv_index",
        "forecast_days": 1,
        "timezone": "auto",
    }
    data = await _get_json(FORECAST_URL, params)
    h = data["hourly"]
    times = h["time"]
    values = h["uv_index"]
    now = dt.datetime.now(dt.timezone.utc)

    current_uv = None
    closest_i = 0
    for i, t in enumerate(times):
        hour_dt = dt.datetime.fromisoformat(t).replace(tzinfo=dt.timezone.utc)
        local_now = now + dt.timedelta(minutes=data.get("utc_offset_seconds", 0))
        if abs((hour_dt - local_now).total_seconds()) < abs(
            (dt.datetime.fromisoformat(times[closest_i]).replace(tzinfo=dt.timezone.utc) - local_now).total_seconds()
        ):
            closest_i = i
    current_uv = values[closest_i]

    daily_max = max(values) if values else None

    def uv_label(uv):
        if uv is None:
            return None
        if uv < 3: return "Low"
        if uv < 6: return "Moderate"
        if uv < 8: return "High"
        if uv < 11: return "Very high"
        return "Extreme"

    return {
        "uv_current": current_uv,
        "uv_current_label": uv_label(current_uv),
        "uv_max_today": daily_max,
        "uv_max_label": uv_label(daily_max),
        "hourly": [{"time": times[i], "uv": values[i]} for i in range(len(times))],
    }


@router.get("/air-quality/{lat}/{lon}")
async def air_quality(lat: float, lon: float):
    """European AQI + US AQI + pollutant concentrations."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,"
                   "nitrogen_dioxide,sulphur_dioxide,ozone",
        "timezone": "auto",
    }
    data = await _get_json(AIR_QUALITY_URL, params)
    cur = data.get("current", {})
    e_aqi = cur.get("european_aqi")
    return {
        "european_aqi": e_aqi,
        "european_aqi_label": eu_aqi_label(e_aqi) if e_aqi is not None else None,
        "us_aqi": cur.get("us_aqi"),
        "pm2_5": cur.get("pm2_5"),
        "pm10": cur.get("pm10"),
        "o3": cur.get("ozone"),
        "no2": cur.get("nitrogen_dioxide"),
        "so2": cur.get("sulphur_dioxide"),
        "co": cur.get("carbon_monoxide"),
    }


@router.get("/history/{lat}/{lon}")
async def climate_history(lat: float, lon: float, days: int = Query(365, ge=30, le=366)):
    """Climate stats for the past year: averages, extremes, total rainfall."""
    end = dt.date.today() - dt.timedelta(days=6)  # archive lags ~5 days
    start = end - dt.timedelta(days=days - 1)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
    }
    data = await _get_json(ARCHIVE_URL, params)
    d = data["daily"]
    tmax, tmin, rain = d["temperature_2m_max"], d["temperature_2m_min"], d["precipitation_sum"]
    days_count = max(len(tmax), 1)

    hottest_i = tmax.index(max(tmax))
    coldest_i = tmin.index(min(tmin))
    wettest_i = rain.index(max(rain))

    return {
        "period": {"start": d["time"][0], "end": d["time"][-1], "days": days_count},
        "avg_high": round(sum(tmax) / days_count, 1),
        "avg_low": round(sum(tmin) / days_count, 1),
        "total_precipitation_mm": round(sum(rain), 1),
        "hottest_day": {"date": d["time"][hottest_i], "temp": tmax[hottest_i]},
        "coldest_day": {"date": d["time"][coldest_i], "temp": tmin[coldest_i]},
        "wettest_day": {"date": d["time"][wettest_i], "precipitation_mm": rain[wettest_i]},
    }


@router.get("/compare")
async def compare_cities(cities: str = Query(..., description="Comma-separated city names, e.g. Paris,London,Tokyo")):
    """Side-by-side current weather for several cities (2-6)."""
    names = [c.strip() for c in cities.split(",") if c.strip()][:6]
    if len(names) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 comma-separated cities")

    results = []
    for name in names:
        found = await geocode_city(name, count=1)
        if not found:
            results.append({"query": name, "error": "not found"})
            continue
        place = found[0]
        params = {
            "latitude": place["lat"],
            "longitude": place["lon"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "weather_code,wind_speed_10m",
            "timezone": "auto",
        }
        data = await _get_json(FORECAST_URL, params)
        cur = data["current"]
        results.append({
            "query": name,
            "name": place["name"],
            "country": place["country"],
            "lat": place["lat"],
            "lon": place["lon"],
            "temperature": cur.get("temperature_2m"),
            "feels_like": cur.get("apparent_temperature"),
            "humidity": cur.get("relative_humidity_2m"),
            "description": describe_code(cur.get("weather_code", -1)),
            "wind_speed": cur.get("wind_speed_10m"),
        })
    return {"cities": results}

import { useEffect, useState } from 'react'
import { Sun, Wind, Droplets, CalendarRange, Leaf } from 'lucide-react'
import { API_URL } from './config'
import './WeatherExtrasPanel.css'

function getWeatherEmoji(description) {
  const d = (description || '').toLowerCase()
  if (d.includes('thunder')) return '⛈️'
  if (d.includes('snow')) return '❄️'
  if (d.includes('rain') || d.includes('drizzle') || d.includes('shower')) return '🌧️'
  if (d.includes('overcast')) return '☁️'
  if (d.includes('cloud')) return '⛅'
  if (d.includes('clear')) return '☀️'
  if (d.includes('fog') || d.includes('mist')) return '🌫️'
  return '🌡️'
}

function uvColor(uv) {
  if (uv == null) return '#6b7280'
  if (uv < 3) return '#22c55e'
  if (uv < 6) return '#eab308'
  if (uv < 8) return '#f97316'
  if (uv < 11) return '#ef4444'
  return '#a855f7'
}

function aqiColor(aqi) {
  if (aqi == null) return '#6b7280'
  if (aqi <= 20) return '#22c55e'
  if (aqi <= 40) return '#a3e635'
  if (aqi <= 60) return '#eab308'
  if (aqi <= 80) return '#f97316'
  if (aqi <= 100) return '#ef4444'
  return '#a855f7'
}

function formatDayLabel(dateStr, index) {
  if (index === 0) return 'Today'
  const parsed = new Date(`${dateStr}T00:00:00`)
  return parsed.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })
}

/**
 * Extended insights for the selected city, powered by Open-Meteo
 * (free, no API key): UV index, air quality, and a 16-day outlook.
 */
function WeatherExtrasPanel({ lat, lon, city }) {
  const [tab, setTab] = useState('uv')
  const [uv, setUv] = useState(null)
  const [air, setAir] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!lat || !lon) return
    let cancelled = false
    setLoading(true)
    setFailed(false)

    Promise.allSettled([
      fetch(`${API_URL}/openmeteo/uv/${lat}/${lon}`).then((r) => (r.ok ? r.json() : Promise.reject())),
      fetch(`${API_URL}/openmeteo/air-quality/${lat}/${lon}`).then((r) => (r.ok ? r.json() : Promise.reject())),
      fetch(`${API_URL}/openmeteo/forecast/${lat}/${lon}?days=16`).then((r) =>
        r.ok ? r.json() : Promise.reject()
      ),
    ]).then(([uvRes, airRes, fcRes]) => {
      if (cancelled) return
      if (uvRes.status === 'fulfilled') setUv(uvRes.value)
      if (airRes.status === 'fulfilled') setAir(airRes.value)
      if (fcRes.status === 'fulfilled') setForecast(fcRes.value)
      if (uvRes.status === 'rejected' && airRes.status === 'rejected' && fcRes.status === 'rejected') {
        setFailed(true)
      }
      setLoading(false)
    })

    return () => {
      cancelled = true
    }
  }, [lat, lon])

  if (!lat || !lon) return null

  return (
    <div className="extras-panel">
      <div className="extras-tabs">
        <button className={tab === 'uv' ? 'extras-tab active' : 'extras-tab'} onClick={() => setTab('uv')}>
          <Sun size={13} /> UV Index
        </button>
        <button className={tab === 'air' ? 'extras-tab active' : 'extras-tab'} onClick={() => setTab('air')}>
          <Leaf size={13} /> Air Quality
        </button>
        <button className={tab === 'forecast' ? 'extras-tab active' : 'extras-tab'} onClick={() => setTab('forecast')}>
          <CalendarRange size={13} /> 16-Day
        </button>
      </div>

      {loading && <div className="extras-loading">Loading insights…</div>}
      {failed && !uv && !air && !forecast && (
        <div className="extras-loading">Extended data unavailable right now.</div>
      )}

      {tab === 'uv' && uv && (
        <div className="extras-body">
          <div className="extras-highlight">
            <span className="extras-big" style={{ color: uvColor(uv.uv_current) }}>
              {uv.uv_current != null ? uv.uv_current : '–'}
            </span>
            <div>
              <p className="extras-label">UV right now in {city}</p>
              <p className="extras-sub">
                {uv.uv_current_label || '—'} · today's max {uv.uv_max_today != null ? uv.uv_max_today : '–'} ({uv.uv_max_label || '—'})
              </p>
            </div>
          </div>
          {uv.uv_max_today >= 6 && (
            <p className="extras-tip">
              ☀️ Use sunscreen and sunglasses between 10am–4pm today.
            </p>
          )}
        </div>
      )}

      {tab === 'air' && air && (
        <div className="extras-body">
          <div className="extras-highlight">
            <span className="extras-big" style={{ color: aqiColor(air.european_aqi) }}>
              {air.european_aqi != null ? air.european_aqi : '–'}
            </span>
            <div>
              <p className="extras-label">Air quality in {city}</p>
              <p className="extras-sub">
                {air.european_aqi_label || '—'} · US AQI {air.us_aqi != null ? air.us_aqi : '–'}
              </p>
            </div>
          </div>
          <div className="extras-grid">
            <div className="extras-stat"><Droplets size={13} /> PM2.5: {air.pm2_5 ?? '–'}</div>
            <div className="extras-stat"><Wind size={13} /> PM10: {air.pm10 ?? '–'}</div>
            <div className="extras-stat"><Leaf size={13} /> O₃: {air.o3 ?? '–'}</div>
            <div className="extras-stat"><Leaf size={13} /> NO₂: {air.no2 ?? '–'}</div>
          </div>
          {(air.european_aqi ?? 0) > 60 && (
            <p className="extras-tip">😮‍💨 Air is polluted — sensitive groups should limit outdoor exertion.</p>
          )}
        </div>
      )}

      {tab === 'forecast' && forecast && (
        <div className="extras-body extras-forecast-scroll">
          {forecast.forecast.map((day, i) => (
            <div key={day.date} className="extras-forecast-row">
              <span className="extras-forecast-day">{formatDayLabel(day.date, i)}</span>
              <span className="extras-forecast-emoji" title={day.description}>
                {getWeatherEmoji(day.description)}
              </span>
              <span className="extras-forecast-desc">{day.description}</span>
              <span className="extras-forecast-rain">
                💧 {day.precipitation_probability != null ? day.precipitation_probability : 0}%
              </span>
              <span className="extras-forecast-temps">
                {day.temp_max != null ? Math.round(day.temp_max) : '–'}° /{' '}
                {day.temp_min != null ? Math.round(day.temp_min) : '–'}°
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default WeatherExtrasPanel

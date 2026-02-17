import requests
from typing import List
import datetime

from goosepaper.storyprovider.storyprovider import StoryProvider
from goosepaper.story import Story
from goosepaper.util import PlacementPreference

_WEATHER_CODES = {
    0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime Fog",
    51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
    56: "Freezing Drizzle", 57: "Heavy Freezing Drizzle",
    61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    66: "Freezing Rain", 67: "Heavy Freezing Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 77: "Snow Grains",
    80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
    85: "Light Snow Showers", 86: "Heavy Snow Showers",
    95: "Thunderstorms", 96: "Thunderstorms w/ Hail", 99: "Severe Thunderstorms",
}

_WEATHER_ICONS = {
    0: "\u2600", 1: "\U0001f324", 2: "\u26c5", 3: "\u2601",
    45: "\U0001f32b", 48: "\U0001f32b",
    51: "\U0001f326", 53: "\U0001f327", 55: "\U0001f327",
    61: "\U0001f326", 63: "\U0001f327", 65: "\U0001f327",
    71: "\U0001f328", 73: "\u2744", 75: "\u2744",
    80: "\U0001f326", 81: "\U0001f327", 82: "\U0001f327",
    95: "\u26c8", 96: "\u26c8", 99: "\u26c8",
}

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class FiveDayForecastProvider(StoryProvider):
    def __init__(
        self,
        lat: float,
        lon: float,
        F: bool = True,
        timezone: str = "America/New_York",
    ):
        self.lat = lat
        self.lon = lon
        self.F = F
        self.timezone = timezone.replace("/", "%2F")

    def get_stories(self, limit: int = 1, **kwargs) -> List[Story]:
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={self.lat}&longitude={self.lon}"
                f"&daily=weathercode,temperature_2m_max,temperature_2m_min,"
                f"precipitation_probability_max,wind_speed_10m_max"
                f"&temperature_unit={'fahrenheit' if self.F else 'celsius'}"
                f"&wind_speed_unit={'mph' if self.F else 'kmh'}"
                f"&timezone={self.timezone}"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            daily = data["daily"]

            unit = "F" if self.F else "C"
            today = datetime.date.today()

            # Single-line compact forecast
            parts = []
            for i in range(5):
                day = today + datetime.timedelta(days=i)
                day_name = "Today" if i == 0 else _DAY_NAMES[day.weekday()]
                code = daily["weathercode"][i]
                high = daily["temperature_2m_max"][i]
                low = daily["temperature_2m_min"][i]
                icon = _WEATHER_ICONS.get(code, "")
                parts.append(f"<b>{day_name}</b> {icon} {high:.0f}\u00b0/{low:.0f}\u00b0")

            forecast_line = " &nbsp;\u2502&nbsp; ".join(parts)

            today_code = daily["weathercode"][0]
            today_desc = _WEATHER_CODES.get(today_code, "Unknown")

            body_html = f'<p style="font-size: 10pt; text-align: center;">{forecast_line}</p>'

            return [
                Story(
                    headline=f"5-Day Forecast \u2014 {today_desc}",
                    body_html=body_html,
                    byline="Open-Meteo",
                    placement_preference=PlacementPreference.NONE,
                )
            ]
        except Exception as e:
            print(f"Forecast provider error: {e}")
            return []

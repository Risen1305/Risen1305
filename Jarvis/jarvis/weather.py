"""Current weather from Open-Meteo (free, no API key)."""
import requests

WMO = {
    0: "clear skies", 1: "mostly clear skies", 2: "partly cloudy skies", 3: "overcast skies",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "heavy showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}

TIMEOUT = 6


class Weather:
    def __init__(self, cfg: dict):
        self.loc_cfg = cfg["location"]
        self.units = cfg["weather"].get("units", "celsius")
        self._location = None  # (lat, lon, place name)

    def location(self):
        if self._location:
            return self._location
        c = self.loc_cfg
        if "latitude" in c and "longitude" in c:
            self._location = (c["latitude"], c["longitude"], c.get("city") or "your area")
        elif c.get("city"):
            r = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": c["city"], "count": 1}, timeout=TIMEOUT,
            )
            hit = r.json()["results"][0]
            self._location = (hit["latitude"], hit["longitude"], hit["name"])
        else:
            r = requests.get("https://ipinfo.io/json", timeout=TIMEOUT).json()
            lat, lon = (float(x) for x in r["loc"].split(","))
            self._location = (lat, lon, r.get("city") or "your area")
        return self._location

    def current(self) -> dict:
        lat, lon, place = self.location()
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "temperature_unit": self.units, "wind_speed_unit": "mph" if self.units == "fahrenheit" else "kmh",
                "timezone": "auto", "forecast_days": 1,
            },
            timeout=TIMEOUT,
        ).json()
        cur, day = r["current"], r["daily"]
        return {
            "place": place,
            "temp": round(cur["temperature_2m"]),
            "feels_like": round(cur["apparent_temperature"]),
            "sky": WMO.get(cur["weather_code"], "mixed conditions"),
            "high": round(day["temperature_2m_max"][0]),
            "low": round(day["temperature_2m_min"][0]),
            "rain_chance": day["precipitation_probability_max"][0] or 0,
        }

    def spoken(self) -> str:
        """A short, natural sentence, or '' if the weather can't be fetched."""
        try:
            w = self.current()
        except Exception:
            return ""
        s = f"It's {w['temp']} degrees in {w['place']}, with {w['sky']}"
        if abs(w["feels_like"] - w["temp"]) >= 3:
            s += f", though it feels more like {w['feels_like']}"
        s += f". Today's high is {w['high']}, low {w['low']}"
        if w["rain_chance"] >= 40:
            s += f", and there's a {w['rain_chance']} percent chance of rain, so you may want an umbrella"
        return s + "."

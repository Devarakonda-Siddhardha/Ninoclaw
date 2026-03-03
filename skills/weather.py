"""
Weather skill — uses open-meteo.com (100% free, no API key)
"""
import requests

SKILL_INFO = {
    "name": "weather",
    "description": "Get current weather and temperature for any city worldwide",
    "version": "1.0",
    "icon": "🌤️",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather conditions, temperature, humidity and wind for any city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. Hyderabad"}
            },
            "required": ["city"]
        }
    }
}]

_WMO = {
    0:"Clear sky", 1:"Mainly clear", 2:"Partly cloudy", 3:"Overcast",
    45:"Foggy", 48:"Icy fog", 51:"Light drizzle", 53:"Moderate drizzle",
    55:"Dense drizzle", 61:"Slight rain", 63:"Moderate rain", 65:"Heavy rain",
    71:"Slight snow", 73:"Moderate snow", 75:"Heavy snow", 80:"Rain showers",
    81:"Moderate showers", 82:"Violent showers", 95:"Thunderstorm",
    96:"Thunderstorm with hail",
}

def execute(tool_name, arguments):
    if tool_name != "get_weather":
        return None
    city = arguments.get("city", "")
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en"}, timeout=10
        ).json()
        if not geo.get("results"):
            return f"❌ City not found: {city}"
        r = geo["results"][0]
        lat, lon = r["latitude"], r["longitude"]
        name = r.get("name", city)
        country = r.get("country", "")

        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
                "temperature_unit": "celsius", "wind_speed_unit": "kmh"
            }, timeout=10
        ).json()
        c = w["current"]
        temp     = c["temperature_2m"]
        feels    = c["apparent_temperature"]
        humidity = c["relative_humidity_2m"]
        wind     = c["wind_speed_10m"]
        cond     = _WMO.get(c["weather_code"], "Unknown")
        return (f"🌍 **{name}, {country}**\n"
                f"🌡️ {temp}°C (feels like {feels}°C)\n"
                f"☁️ {cond}\n"
                f"💧 Humidity: {humidity}%\n"
                f"💨 Wind: {wind} km/h")
    except Exception as e:
        return f"❌ Weather error: {e}"

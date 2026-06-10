from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class WeatherSnapshot:
    city: str
    temperature_c: float | None
    description: str


class WeatherService:
    def __init__(self, city: str, latitude: float, longitude: float) -> None:
        self.city = city
        self.latitude = latitude
        self.longitude = longitude

    def fetch(self) -> WeatherSnapshot:
        url = (
            "https://api.open-meteo.com/v1/forecast?"
            + urllib.parse.urlencode(
                {
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "current": "temperature_2m,weather_code",
                    "timezone": "auto",
                }
            )
        )
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            current = payload.get("current", {})
            temp = current.get("temperature_2m")
            code = current.get("weather_code")
            return WeatherSnapshot(self.city, temp, _code_to_description(code))
        except Exception:
            return WeatherSnapshot(self.city, None, "Cevrimdisi")


def _code_to_description(code: int | None) -> str:
    mapping = {
        0: "Acik",
        1: "Cok az bulutlu",
        2: "Parcali bulutlu",
        3: "Bulutlu",
        45: "Sisli",
        48: "Kirisik sis",
        51: "Hafif sisli",
        61: "Yagisli",
        63: "Orta yagisli",
        65: "Siddetli yagisli",
        71: "Karla karisik",
        80: "Saganak",
        95: "Firtinali",
    }
    return mapping.get(code, "Bilinmiyor")


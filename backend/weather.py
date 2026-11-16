"""
weather.py

Gets the hourly weather forecast for a SunCast city from the Open-Meteo
forecast API (free, no key needed).

Returns a table with one row per hour:
    time        local Pakistan time
    radiation   shortwave radiation reaching the ground (W/m2)
    temp_c      air temperature at 2 m (C)
"""

import time

import pandas as pd
import requests

# Same coordinates we used for the NASA POWER data
CITIES = {
    "Lahore": (31.52, 74.36),
    "Karachi": (24.86, 67.00),
    "Islamabad": (33.68, 73.05),
    "Peshawar": (34.02, 71.58),
    "Multan": (30.16, 71.52),
}

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def get_forecast(city, days, retries=2):
    """Hourly forecast for the next `days` days (1 to 7) for one city."""
    lat, lon = CITIES[city]
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "shortwave_radiation,temperature_2m",
        "timezone": "Asia/Karachi",
        "forecast_days": days,
    }

    for attempt in range(retries):
        try:
            response = requests.get(FORECAST_URL, params=params, timeout=15)
            response.raise_for_status()
            hourly = response.json()["hourly"]
            break
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(1)  # short wait, then one more try

    df = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "radiation": hourly["shortwave_radiation"],
        "temp_c": hourly["temperature_2m"],
    })

    # Fill any small gaps so the model never gets empty values
    df["radiation"] = df["radiation"].fillna(0).clip(lower=0)
    df["temp_c"] = df["temp_c"].interpolate().bfill().ffill()
    return df

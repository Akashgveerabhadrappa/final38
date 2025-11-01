import requests
import pandas as pd
from flask import current_app

def get_lat_lon(city_name):
    """
    Uses Open-Meteo Geocoding to get lat/lon for a city.
    """
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}"
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Will raise an error for bad responses
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            return data["results"][0]["latitude"], data["results"][0]["longitude"]
    except Exception as e:
        current_app.logger.error(f"Error getting coordinates for {city_name}: {e}")
    return None, None

def fetch_current_weather(lat, lon):
    """
    Uses Open-Meteo to get the CURRENT weather for a lat/lon.
    """
    if not lat or not lon:
        return None
    try:
        # This is the "current weather" API call
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation"
            f"&timezone=Asia/Kolkata" # Use a standard timezone
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Return the data in a simple dictionary
        if "current" in data:
            return {
                "temp": data["current"]["temperature_2m"],
                "humidity": data["current"]["relative_humidity_2m"],
                "rainfall": data["current"]["precipitation"]
            }
    except Exception as e:
        current_app.logger.error(f"Error fetching current weather for lat/lon {lat}/{lon}: {e}")
    return None
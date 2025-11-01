import os
import json
import time
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict
import pandas as pd
import numpy as np
import requests
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

from .utils import log, log_exception, setup_session, GEO_CACHE_FILE

# --- Configuration ---
# Path is relative to the project root
DATA_DIR = 'data' 
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
GEOCODER_API = "https://geocode.maps.co/search"
PREDICTION_FUTURE_DAYS = 90

# --- 1. Geocoding & Weather ---

def load_geo_cache() -> Dict:
    if os.path.exists(GEO_CACHE_FILE):
        try:
            with open(GEO_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_geo_cache(cache: Dict):
    try:
        with open(GEO_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        log(f"[Geocode] Warning: Failed to save cache: {e}")

def geocode_market(market_name: str, district: str, state: str, session: requests.Session) -> Tuple[Optional[float], Optional[float]]:
    cache = load_geo_cache()
    key = f"{market_name}|{district}|{state}".lower()
    
    if key in cache:
        log(f"[Geocode] Cache HIT for {key}")
        return cache[key]["lat"], cache[key]["lon"]
    
    log(f"[Geocode] Cache MISS for {key}. Querying API...")
    query = f"{market_name}, {district}, {state}"
    try:
        res = session.get(GEOCODER_API, params={"q": query}, timeout=10)
        res.raise_for_status()
        results = res.json()
        
        if not results:
            log(f"[Geocode] No results for {query}")
            return None, None
            
        chosen = results[0]
        lat = float(chosen["lat"])
        lon = float(chosen["lon"])
        
        cache[key] = {"lat": lat, "lon": lon, "name": chosen.get("display_name")}
        save_geo_cache(cache)
        log(f"[Geocode] Success: {query} -> {lat}, {lon}")
        return lat, lon
        
    except Exception as e:
        log_exception(f"[Geocode] API query failed for {query}", e)
        return None, None

def get_weather_data(lat: float, lon: float, start_date: str, end_date: str, is_forecast: bool, session: requests.Session) -> Optional[Dict]:
    url = OPEN_METEO_FORECAST if is_forecast else OPEN_METEO_ARCHIVE
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto"
    }
    
    if is_forecast:
        params["forecast_days"] = 16
    else:
        params["start_date"] = start_date
        params["end_date"] = end_date

    try:
        res = session.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        if not data.get("daily") or not data["daily"].get("time"):
            log(f"[Weather] API returned no daily data for {lat},{lon}")
            return None
            
        weather_dict = {}
        for i, date_str in enumerate(data["daily"]["time"]):
            weather_dict[date_str] = {
                "temp_max": data["daily"]["temperature_2m_max"][i],
                "temp_min": data["daily"]["temperature_2m_min"][i],
                "precip": data["daily"]["precipitation_sum"][i],
                "wmo": data["daily"]["weathercode"][i]
            }
        log(f"[Weather] Fetched {len(weather_dict)} days of data for {lat},{lon}")
        return weather_dict
        
    except Exception as e:
        log_exception(f"[Weather] API query failed for {lat},{lon}", e)
        return None

# --- 2. Model Training & Prediction (Copied from your file) ---

def preprocess_data(df: pd.DataFrame, weather_data: Dict) -> Optional[pd.DataFrame]:
    try:
        df = df.rename(columns={
            "Reported Date": "date",
            "Modal Price (Rs./Quintal)": "modal_price",
            "Arrivals (Tonnes)": "arrivals_tonnes"
        })

        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors='coerce')
        df["modal_price"] = pd.to_numeric(df["modal_price"], errors="coerce")
        df["arrivals_tonnes"] = pd.to_numeric(df["arrivals_tonnes"], errors="coerce")
        
        df = df.dropna(subset=["date", "modal_price"])
        df = df.sort_values(by="date").reset_index(drop=True)
        
        if df.empty:
            log("[Preprocess] No data left after cleaning.")
            return None

        weather_df = pd.DataFrame.from_dict(weather_data, orient="index")
        weather_df.index.name = "date_str"
        weather_df = weather_df.reset_index()
        weather_df["date"] = pd.to_datetime(weather_df["date_str"])
        
        merged = pd.merge_asof(
            df.sort_values("date"),
            weather_df.sort_values("date"),
            on="date",
            direction="nearest",
            tolerance=pd.Timedelta(days=1)
        )
        
        merged["doy"] = merged["date"].dt.dayofyear
        merged["month"] = merged["date"].dt.month
        merged["year"] = merged["date"].dt.year
        merged["dow"] = merged["date"].dt.weekday
        merged["arrivals_tonnes"] = merged["arrivals_tonnes"].fillna(0)
        
        final_cols = [
            "date", "modal_price", "arrivals_tonnes", "temp_max", "temp_min", 
            "precip", "doy", "month", "year", "dow"
        ]
        
        merged = merged.dropna(subset=[col for col in final_cols if col not in ["arrivals_tonnes"]])
        log(f"[Preprocess] Merged with weather, final shape: {merged.shape}")
        return merged[final_cols]
        
    except Exception as e:
        log_exception("[Preprocess] Failed", e)
        return None

def train_model(df: pd.DataFrame) -> Tuple[Optional[object], Dict]:
    metrics = {"r2_score": 0.0, "train_rows": 0}
    try:
        features = ["arrivals_tonnes", "temp_max", "temp_min", "precip", "doy", "month", "year", "dow"]
        target = "modal_price"
        
        X = df[features]
        y = df[target]
        
        if X.empty or y.empty or len(X) < 20:
            log("[Model] Not enough data to train.")
            return None, metrics

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        metrics["train_rows"] = len(X_train)
        
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1, max_depth=10)
        model.fit(X_train, y_train)
        
        if not y_test.empty:
            y_pred = model.predict(X_test)
            metrics["r2_score"] = float(r2_score(y_test, y_pred))
        
        log(f"[Model] Trained. R2={metrics['r2_score']:.4f}")
        return model, metrics
        
    except Exception as e:
        log_exception("[Model] Training failed", e)
        return None, metrics

def forecast(model: object, future_date: datetime, weather_features: Dict, last_arrival: float) -> Optional[float]:
    try:
        feat_row = {
            "arrivals_tonnes": last_arrival,
            "temp_max": float(weather_features.get("temp_max", 0.0)),
            "temp_min": float(weather_features.get("temp_min", 0.0)),
            "precip": float(weather_features.get("precip", 0.0)),
            "doy": int(future_date.timetuple().tm_yday),
            "month": int(future_date.month),
            "year": int(future_date.year),
            "dow": int(future_date.weekday()),
        }
        
        pred_price = float(model.predict(pd.DataFrame([feat_row]))[0])
        return pred_price
        
    except Exception as e:
        log_exception("[Forecast] Failed", e)
        return None

# --- 3. Main Orchestrator ---

def run_price_prediction(crop_name: str, district_name: str, session: requests.Session) -> Optional[Dict]:
    """Main function to process a single crop for price."""
    
    csv_file = os.path.join(DATA_DIR, f"{crop_name.lower().replace('/','_')}.csv")
    
    if not os.path.exists(csv_file):
        log(f"[Data] Price CSV not found: {csv_file}. Skipping price forecast.")
        return None
        
    try:
        raw_df = pd.read_csv(csv_file)
    except Exception as e:
        log_exception(f"[Data] Failed to read {csv_file}", e)
        return None

    district_df = raw_df[raw_df["District Name"].str.strip().str.lower() == district_name.strip().lower()].copy()
    
    if district_df.empty:
        log(f"[Data] No data found for district '{district_name}' in '{csv_file}'.")
        return None
        
    try:
        target_market = district_df["Market Name"].mode()[0]
        target_state = district_df["State Name"].mode()[0]
        log(f"[Data] Found {len(district_df)} rows for district. Auto-selected primary market: {target_market}")
    except Exception as e:
        log_exception(f"[Data] Could not determine market/state from CSV", e)
        return None
        
    market_df = district_df[district_df["Market Name"] == target_market].copy()

    lat, lon = geocode_market(target_market, district_name, target_state, session)
    if lat is None:
        log(f"[Weather] Could not geocode market '{target_market}'.")
        return None

    min_date = pd.to_datetime(market_df["Reported Date"], dayfirst=True, errors='coerce').min().strftime("%Y-%m-%d")
    max_date = pd.to_datetime(market_df["Reported Date"], dayfirst=True, errors='coerce').max().strftime("%Y-%m-%d")
    
    hist_weather = get_weather_data(lat, lon, min_date, max_date, is_forecast=False, session=session)
    future_weather_data = get_weather_data(lat, lon, None, None, is_forecast=True, session=session)

    if not hist_weather or not future_weather_data:
        log("[Weather] Failed to get weather data.")
        return None

    processed_df = preprocess_data(market_df, hist_weather)
    if processed_df is None or processed_df.empty:
        log("[Preprocess] No data after preprocessing.")
        return None
        
    model, metrics = train_model(processed_df)
    if model is None:
        log("[Model] Model training failed.")
        return None

    future_date = datetime.now() + timedelta(days=PREDICTION_FUTURE_DAYS)
    latest_forecast_date_str = sorted(future_weather_data.keys())[-1]
    weather_for_future = future_weather_data[latest_forecast_date_str]
    log(f"[Forecast] Using weather from {latest_forecast_date_str} for future date {future_date.date()}")

    last_arrival = processed_df.iloc[-1]["arrivals_tonnes"]
    predicted_price = forecast(model, future_date, weather_for_future, last_arrival)
    
    if predicted_price is None:
        return None

    return {
        "predicted_price": round(predicted_price, 2),
        "market": target_market,
        "prediction_date": future_date.strftime("%Y-%m-%d"),
        "model_r2": round(metrics["r2_score"], 4)
    }
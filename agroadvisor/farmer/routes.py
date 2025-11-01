from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from .forms import RecommendationForm, PricePredictionForm
import pandas as pd
import os
from datetime import datetime, timedelta
import numpy as np
import time 
import requests 

# Import our ML functions and pre-loaded models
from agroadvisor.ml_models import CROP_MODEL, YIELD_MODEL, AVG_YIELD_LOOKUP
from agroadvisor.ml_models.recommender import get_recommendations
from agroadvisor.ml_models.predictor import run_price_prediction, geocode_market
from agroadvisor.ml_models.utils import log_exception, setup_session, log

# Tell the blueprint where to find its templates
farmer_bp = Blueprint('farmer', __name__, template_folder='../templates/farmer')


# ✅ THIS IS YOUR NEW, MORE EFFICIENT WEATHER FUNCTION
def get_weather_data(lat, lon, start_date=None, end_date=None, is_forecast=False, session=None, years=5):
    """
    Fetch weather data (historical or forecast) for a given location using Open-Meteo API.
    If is_forecast=False, it gets multi-year historical data in a *single call*.
    """
    try:
        import pandas as pd
        base_url = (
            "https://api.open-meteo.com/v1/forecast"
            if is_forecast
            else "https://archive-api.open-meteo.com/v1/archive"
        )

        today = datetime.utcnow().date()
        daily_vars = [
            "weathercode",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
        ]
        if not is_forecast:
            daily_vars.append("relative_humidity_2m_mean")
        else:
            daily_vars.append("relativehumidity_2m_mean")

        all_dataframes = []

        if is_forecast:
            # Forecast = single call
            end_dt = today + timedelta(days=7)
            start_dt = today
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": daily_vars,
                "timezone": "auto",
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
            }
            log(f"[Weather] Fetching forecast for {lat},{lon} ({start_dt} to {end_dt})")
            res = session.get(base_url, params=params, timeout=30)
            res.raise_for_status()
            data = res.json()
            if "daily" not in data:
                return None
            df = pd.DataFrame(data["daily"])
            all_dataframes.append(df)
        else:
            # --- THIS IS THE NEW, EFFICIENT LOGIC ---
            # Historical multi-year aggregation in ONE CALL
            end_dt = today - timedelta(days=3) # End date is ~yesterday
            start_dt = today - timedelta(days=(years * 365)) # Start date is 5 years ago
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": daily_vars,
                "timezone": "auto",
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
                "models": "era5", # Use a consistent historical model
            }
            log(f"[Weather] Fetching *single* archive for {start_dt} to {end_dt}")
            res = session.get(base_url, params=params, timeout=30)
            res.raise_for_status() # This will catch the 429 error if it happens
            data = res.json()
            if "daily" in data and data["daily"]:
                df = pd.DataFrame(data["daily"])
                all_dataframes.append(df)
            else:
                log(f"[Weather] No data in single archive call.")
            # --- END OF NEW LOGIC ---

        if not all_dataframes:
            log("[Weather] No valid weather data found.")
            return None

        weather_df = pd.concat(all_dataframes, ignore_index=True)
        weather_df["date"] = pd.to_datetime(weather_df["time"])
        weather_df.sort_values("date", inplace=True)
        
        # --- Handle potential missing humidity column ---
        if "relative_humidity_2m_mean" in weather_df.columns:
            weather_df["humidity"] = weather_df["relative_humidity_2m_mean"]
        elif "relativehumidity_2m_mean" in weather_df.columns:
            weather_df["humidity"] = weather_df["relativehumidity_2m_mean"]
        else:
            weather_df["humidity"] = np.nan # Create an empty column if not present

        # --- Seasonal groupings ---
        rabi = weather_df[weather_df['date'].dt.month.isin([10, 11, 12, 1, 2, 3])]
        kharif = weather_df[weather_df['date'].dt.month.isin([6, 7, 8, 9, 10])]
        summer = weather_df[weather_df['date'].dt.month.isin([3, 4, 5, 6])]
        whole_year = weather_df # For the "Whole Year" option

        def season_stats(df, num_years):
            if df.empty or num_years == 0:
                # Return sensible defaults if no data
                return {"avg_temp": 25.0, "rainfall": 1000.0, "humidity": 60.0}
            
            # Calculate average *annual* rainfall for that season
            total_rainfall = df["precipitation_sum"].sum()
            avg_annual_rainfall = total_rainfall / num_years

            return {
                "avg_temp": ((df["temperature_2m_max"] + df["temperature_2m_min"]) / 2).mean(),
                "rainfall": avg_annual_rainfall,
                "humidity": df["humidity"].mean(),
            }

        num_years_found = len(weather_df["date"].dt.year.unique())
        if num_years_found == 0: num_years_found = 1 # Avoid division by zero

        seasonal_summary = {
            "Rabi": season_stats(rabi, num_years_found),
            "Kharif": season_stats(kharif, num_years_found),
            "Summer": season_stats(summer, num_years_found),
            "Whole Year": season_stats(whole_year, num_years_found)
        }

        log(f"[Weather] Merged {num_years_found} years -> {len(weather_df)} days total.")
        log(f"[Weather] Seasonal summary: {seasonal_summary}")

        # --- Optional: make old-style dict for backward compatibility ---
        weather_dict = {}
        for _, row in weather_df.iterrows():
            weather_dict[row["time"]] = {
                "temp_max": row.get("temperature_2m_max"),
                "temp_min": row.get("temperature_2m_min"),
                "precip": row.get("precipitation_sum"),
                "humidity": row.get("humidity"),
                "weathercode": row.get("weathercode"),
            }

        return {
            "daily_data": weather_dict,
            "seasonal_summary": seasonal_summary,
        }

    except Exception as e:
        log_exception("[Weather] Error fetching data", e)
        return None



# ---------------- ROUTES ---------------- #

@farmer_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Your Dashboard')


@farmer_bp.route('/recommend', methods=['GET', 'POST'])
@login_required
def recommend():
    form = RecommendationForm()
    results = None
    session = setup_session() # Use one session for all API calls

    # --- THIS IS THE NEW CODE TO POPULATE DROPDOWNS ---
    try:
        # 1. Load District choices from your market CSV
        markets_path = os.path.join(current_app.config['DATA_DIR'], 'agmarknet_state_district_market.csv')
        market_df = pd.read_csv(markets_path)
        # Add a "Select..." option at the top
        district_choices = [("", "Select a District")] + sorted([(d, d) for d in market_df['district'].unique()])
        form.district.choices = district_choices
        
        # 2. Load Season choices (from your yield CSV)
        yield_path = os.path.join(current_app.config['DATA_DIR'], 'crop-wise-area-production-yield.csv')
        yield_df = pd.read_csv(yield_path)
        season_choices = [("", "Select a Season")] + sorted([(s, s) for s in yield_df['season'].unique()])
        form.season.choices = season_choices

    except FileNotFoundError as e:
        log_exception("Error loading CSVs for recommend form", e)
        flash('Error: Data files for form choices are missing.', 'danger')
    except Exception as e:
        # Handle cases where config isn't loaded yet (like db migration)
        log(f"Could not load form choices, probably running a command: {e}")
        pass # Allow the form to load empty
    # --- END OF NEW CODE ---


    if form.validate_on_submit():
        if not CROP_MODEL or not YIELD_MODEL:
            log("Error: Recommender models not loaded.")
            flash('Server is busy, models are not loaded. Please try again later.', 'danger')
            return redirect(url_for('farmer.recommend'))

        try:
            data = form.data
            district_name = data['district']
            selected_season = data['season'] 
            log(f"New recommendation request from {current_user.email} for {district_name} (Selected Season: {selected_season})")

            # --- Geocode ---
            lat, lon = geocode_market(
                market_name=district_name,
                district=district_name,
                state="India", # Geocoder works better with a state/country
                session=session
            )

            if lat is None or lon is None:
                flash(f'Could not find location data for "{district_name}".', 'danger')
                return render_template('recommend.html', title='Crop Recommendation', form=form)

            # --- Weather Fetch (Past 5 years + Seasonal Analysis) ---
            weather_info = get_weather_data(lat, lon, is_forecast=False, session=session, years=5)
            
            if not weather_info or "seasonal_summary" not in weather_info:
                flash(f'Could not fetch weather data for "{district_name}".', 'danger')
                return render_template('recommend.html', title='Crop Recommendation', form=form)
            
            seasonal_stats = weather_info["seasonal_summary"]

            # Get the stats for the season the farmer *selected*
            current_stats = seasonal_stats.get(selected_season, seasonal_stats["Whole Year"])
            log(f"Using stats for selected season: {selected_season}")

            try:
                # Use the pre-calculated seasonal stats
                data['temperature'] = current_stats["avg_temp"]
                data['rainfall'] = current_stats["rainfall"]
                data['humidity'] = current_stats["humidity"]

                # Handle potential NaN values from calculations
                if np.isnan(data['temperature']): data['temperature'] = 25.0
                if np.isnan(data['rainfall']): data['rainfall'] = 1000.0
                if np.isnan(data['humidity']): data['humidity'] = 60.0

                log(f"Final Weather Inputs -> Temp={data['temperature']:.2f}, Rainfall={data['rainfall']:.2f}, Humidity={data['humidity']:.2f}")

            except Exception as e:
                log_exception("Error applying weather stats", e)
                flash('Error processing weather data.', 'danger')
                return render_template('recommend.html', title='Crop Recommendation', form=form)

            # --- Crop recommendations ---
            top_5_crops = get_recommendations(data, CROP_MODEL, YIELD_MODEL, AVG_YIELD_LOOKUP)
            if not top_5_crops:
                flash('No crop recommendations found.', 'warning')
                return render_template('recommend.html', title='Recommendation', form=form)

            # --- Price prediction ---
            combined_results = []
            for crop_data in top_5_crops:
                # No time.sleep() needed thanks to efficient weather API call
                
                crop_name = crop_data['Crop_Name']
                price_result = run_price_prediction(crop_name, district_name, session=session)

                if price_result:
                    crop_data.update(price_result)
                else:
                    crop_data['predicted_price'] = 'N/A'
                    crop_data['market'] = 'N/A'
                
                # Add the season we're recommending for
                crop_data['Season'] = selected_season 
                combined_results.append(crop_data)

            results = combined_results

        except Exception as e:
            log_exception("Unhandled error in /recommend route", e)
            flash(f'An error occurred: {e}', 'danger')

    return render_template('recommend.html', title='Crop Recommendation', form=form, results=results)


@farmer_bp.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    form = PricePredictionForm()
    result = None
    historical_data_json = None # For the graph
    forecast_data_json = None   # For the graph

    try:
        # Use current_app.config to get the correct data path
        commodities_path = os.path.join(current_app.config['DATA_DIR'], 'commodities.csv')
        markets_path = os.path.join(current_app.config['DATA_DIR'], 'agmarknet_state_district_market.csv')
        
        commodity_df = pd.read_csv(commodities_path)
        market_df = pd.read_csv(markets_path)

        form.crop.choices = [("", "Select a Crop")] + sorted([(c, c) for c in commodity_df['Commodity'].unique()])
        form.district.choices = [("", "Select a District")] + sorted([(d, d) for d in market_df['district'].unique()])

    except FileNotFoundError as e:
        log_exception("Error loading CSVs for predict form", e)
        flash(f'Error: Could not find data files. Make sure "commodities.csv" and "agmarknet_state_district_market.csv" are in your "data" folder.', 'danger')
    except Exception as e:
        log_exception(f"Could not load form choices: {e}", e)
        flash(f"An error occurred while loading form options: {e}", 'danger')

    if form.validate_on_submit():
        try:
            crop_name = form.crop.data
            district_name = form.district.data
            log(f"New price prediction request from {current_user.email} for {crop_name} in {district_name}")
            
            session = setup_session()
            price_result = run_price_prediction(
                crop_name=crop_name,
                district_name=district_name,
                session=session
            )
            
            if price_result:
                price_result['crop_name'] = crop_name
                price_result['district_name'] = district_name
                result = price_result
                
                # --- THIS IS THE NEW CODE TO CREATE THE GRAPH DATA ---
                
                # 1. Process Historical Data
                if 'historical_df' in price_result and not price_result['historical_df'].empty:
                    hist_df = price_result['historical_df'].copy()
                    # Ensure 'date' column exists and is a string
                    hist_df['date'] = pd.to_datetime(hist_df['date']).dt.strftime('%Y-%m-%d')
                    # Select only the columns we need
                    hist_df = hist_df[['date', 'modal_price']]
                    historical_data_json = hist_df.to_json(orient='records')

                # 2. Process Forecast Data
                if 'forecast_df' in price_result and not price_result['forecast_df'].empty:
                    fcst_df = price_result['forecast_df'].copy()
                    fcst_df['date'] = pd.to_datetime(fcst_df['date']).dt.strftime('%Y-%m-%d')
                    # Select only the columns we need
                    fcst_df = fcst_df[['date', 'modal_price', 'predicted_price']]
                    forecast_data_json = fcst_df.to_json(orient='records')
                # --- END OF NEW GRAPH CODE ---

            else:
                flash(f'No price data or model could be built for {crop_name} in {district_name}.', 'warning')

        except Exception as e:
            log_exception("Unhandled error in /predict route", e)
            flash(f'An error occurred: {e}', 'danger')

    # Pass the new JSON data to the template
    return render_template(
        'predict.html', 
        title='Predict Price', 
        form=form, 
        result=result,
        historical_data=historical_data_json,
        forecast_data=forecast_data_json
    )
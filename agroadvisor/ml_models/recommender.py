import pandas as pd
import joblib
import os
from .utils import log, log_exception

# --- File Paths ---
# Paths are relative to the project root (agroadvisor_project/)
DATA_DIR = 'data'
MODEL_DIR = 'agroadvisor/ml_models' # <-- This is the new path

YIELD_CSV = os.path.join(DATA_DIR, 'crop-wise-area-production-yield.csv')
YIELD_MODEL_FILE = os.path.join(MODEL_DIR, 'yield_model.joblib')
CROP_MODEL_FILE = os.path.join(MODEL_DIR, 'advanced_crop_model.joblib')

def load_recommender_data():
    """Loads all data files and the model needed for the recommender."""
    try:
        log("Loading recommender data files...")
        log(f"Reading: {YIELD_CSV}")
        df_yield = pd.read_csv(YIELD_CSV)
        
        log(f"Loading yield model from {YIELD_MODEL_FILE}...")
        yield_model = joblib.load(YIELD_MODEL_FILE)
        log("Yield model loaded.")

        log(f"Loading advanced crop model from {CROP_MODEL_FILE}...")
        crop_model = joblib.load(CROP_MODEL_FILE)
        log("Advanced crop model loaded.")

        avg_yield_lookup = df_yield.groupby('crop_name').agg(
            Avg_Yield=('yield', 'mean'),
            Unit=('yield_unit', 'first')
        ).to_dict('index')
        
        log("Recommender models and data loaded successfully.")
        return crop_model, yield_model, avg_yield_lookup
        
    except FileNotFoundError as e:
        log_exception(f"FATAL: Missing file.", e)
        raise
    except Exception as e:
        log_exception(f"FATAL: Error loading recommender data", e)
        raise

def get_recommendations(data: dict, crop_model: object, yield_model: object, avg_yield_lookup: dict) -> list:
    """
    Main recommendation logic (from your original file).
    """
    try:
        # --- 1. Get Environmental Suitability ---
        # Data dict comes from our new WTForm
        model_input = pd.DataFrame([[
            float(data['nitrogen']),
            float(data['phosphorous']),
            float(data['potassium']),
            float(data['ph']),
            float(data['rainfall']),
            float(data['temperature']),
            float(data['humidity'])
        ]], 
            columns=['N', 'P', 'K', 'ph', 'rainfall', 'temperature', 'humidity']
        )
        
        probabilities = crop_model.predict_proba(model_input)[0]
        all_crop_probs = zip(crop_model.classes_, probabilities)
        sorted_crop_probs = sorted(all_crop_probs, key=lambda x: x[1], reverse=True)
        top_5_suitable = sorted_crop_probs[:5]

        log(f"Found top 5 suitable crops: {top_5_suitable}")

        # --- 2. Get Predicted Yield Score for the Top 5 ---
        district = data['district']
        season = data['season']
        final_recommendations = []

        for crop_name, suitability_score in top_5_suitable:
            prediction_input = pd.DataFrame({
                'district_name': [district],
                'crop_name': [crop_name],
                'season': [season]
            })
            
            predicted_yield_score = yield_model.predict(prediction_input)[0]
            final_score = (suitability_score * 0.5) + (predicted_yield_score * 0.5)
            avg_info = avg_yield_lookup.get(crop_name, {'Avg_Yield': 'N/A', 'Unit': ''})
            
            final_recommendations.append({
                'Crop_Name': crop_name,
                'Final_Score': float(final_score),
                'Suitability': float(suitability_score),
                'Predicted_Yield_Score': float(predicted_yield_score),
                'Avg_Historical_Yield': avg_info['Avg_Yield'] if avg_info['Avg_Yield'] != 'N/A' else 'N/A',
                'Unit': avg_info['Unit']
            })

        # --- 4. Sort and return top 5 ---
        top_crops = sorted(final_recommendations, key=lambda x: x['Final_Score'], reverse=True)
        return top_crops

    except Exception as e:
        log_exception("[Recommender] Error in get_recommendations", e)
        return []
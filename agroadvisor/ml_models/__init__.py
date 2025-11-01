from .recommender import load_recommender_data
from .utils import log

# --- Load Models on App Start ---
# This code runs ONCE when the Flask app is imported.
# It loads the heavy models into memory so they are ready for predictions.
try:
    (CROP_MODEL, YIELD_MODEL, AVG_YIELD_LOOKUP) = load_recommender_data()
except Exception as e:
    log(f"CRITICAL: Failed to load ML models on startup. {e}")
    (CROP_MODEL, YIELD_MODEL, AVG_YIELD_LOOKUP) = (None, None, None)
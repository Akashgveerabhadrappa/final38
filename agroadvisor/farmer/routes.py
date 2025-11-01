from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .forms import RecommendationForm, PricePredictionForm
import pandas as pd
import os


# Import our ML functions and pre-loaded models
from agroadvisor.ml_models import CROP_MODEL, YIELD_MODEL, AVG_YIELD_LOOKUP
from agroadvisor.ml_models.recommender import get_recommendations
from agroadvisor.ml_models.predictor import run_price_prediction
from agroadvisor.ml_models.utils import log_exception, setup_session, log

# Tell the blueprint where to find its templates
farmer_bp = Blueprint('farmer', __name__, template_folder='../templates/farmer')

@farmer_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard for farmers."""
    return render_template('dashboard.html', title='Your Dashboard')

@farmer_bp.route('/recommend', methods=['GET', 'POST'])
@login_required
def recommend():
    """
    Page for getting crop recommendations and price predictions.
    This replaces the logic from your original app.py.
    """
    form = RecommendationForm()
    results = None

    if form.validate_on_submit():
        # Check if models are loaded
        if not CROP_MODEL or not YIELD_MODEL:
            log("Error: Recommender models not loaded.")
            flash('Server is busy, models are not loaded. Please try again later or contact support.', 'danger')
            return redirect(url_for('farmer.recommend'))

        try:
            # 1. Get data from the form
            data = form.data
            log(f"New recommendation request from {current_user.email} for {data['district']}")
            
            # 2. Get Top 5 Crop Recommendations
            top_5_crops = get_recommendations(
                data, CROP_MODEL, YIELD_MODEL, AVG_YIELD_LOOKUP
            )
            
            if not top_5_crops:
                flash('No crop recommendations found for these inputs.', 'warning')
                return render_template('recommend.html', title='Recommendation', form=form, results=[])

            # 3. Get Price Predictions for each crop
            session = setup_session()
            combined_results = []

            for crop_data in top_5_crops:
                crop_name = crop_data['Crop_Name']
                log(f"--- Processing price for: {crop_name} in {data['district']} ---")
                
                price_result = run_price_prediction(
                    crop_name=crop_name,
                    district_name=data['district'],
                    session=session
                )
                
                if price_result:
                    crop_data.update(price_result)
                else:
                    crop_data['predicted_price'] = 'N/A'
                    crop_data['market'] = 'N/A'
                
                combined_results.append(crop_data)
            
            results = combined_results

        except Exception as e:
            log_exception("Unhandled error in /recommend route", e)
            flash(f'An error occurred: {e}', 'danger')

    # 4. Show the form on GET request or after POST
    return render_template('recommend.html', title='Crop Recommendation', form=form, results=results)


@farmer_bp.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    """
    Page for getting a standalone price prediction, like in Project 1.
    """
    form = PricePredictionForm()
    result = None

    # --- Load choices for the dropdowns ---
    try:
        # Load crops from commodities.csv
        commodities_path = os.path.join('data', 'commodities.csv')
        commodity_df = pd.read_csv(commodities_path)
        form.crop.choices = [(c, c) for c in sorted(commodity_df['Commodity'].unique())]
        
        # Load districts from agmarknet...csv
        markets_path = os.path.join('data', 'agmarknet_state_district_market.csv')
        market_df = pd.read_csv(markets_path)
        form.district.choices = [(d, d) for d in sorted(market_df['district'].unique())]
        
    except FileNotFoundError as e:
        log_exception("Error loading CSVs for predict form", e)
        flash('Error: Data files for prediction (commodities.csv, agmarknet...) are missing.', 'danger')
        return render_template('predict.html', title='Predict Price', form=form, result=None)

    # --- Handle form submission ---
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
                # Add the form data to the result for display
                price_result['crop_name'] = crop_name
                price_result['district_name'] = district_name
                result = price_result
            else:
                flash(f'No price data or model could be built for {crop_name} in {district_name}.', 'warning')

        except Exception as e:
            log_exception("Unhandled error in /predict route", e)
            flash(f'An error occurred: {e}', 'danger')

    return render_template('predict.html', title='Predict Price', form=form, result=result)
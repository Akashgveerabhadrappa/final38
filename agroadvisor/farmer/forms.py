from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class RecommendationForm(FlaskForm):
    """
    Form for a farmer to get crop recommendations.
    """
    nitrogen = FloatField('Nitrogen (N) in soil (kg/ha)', 
                          validators=[DataRequired(), NumberRange(min=0, max=200)], 
                          default=90.0)
    phosphorous = FloatField('Phosphorous (P) in soil (kg/ha)', 
                             validators=[DataRequired(), NumberRange(min=0, max=200)], 
                             default=40.0)
    potassium = FloatField('Potassium (K) in soil (kg/ha)', 
                           validators=[DataRequired(), NumberRange(min=0, max=200)], 
                           default=40.0)
    ph = FloatField('Soil pH', 
                    validators=[DataRequired(), NumberRange(min=0, max=14)], 
                    default=6.5)
    rainfall = FloatField('Annual Rainfall (mm)', 
                          validators=[DataRequired(), NumberRange(min=100, max=5000)], 
                          default=1000.0)
    temperature = FloatField('Average Temperature (°C)', 
                             validators=[DataRequired(), NumberRange(min=-10, max=50)], 
                             default=25.0)
    humidity = FloatField('Average Humidity (%)', 
                          validators=[DataRequired(), NumberRange(min=0, max=100)], 
                          default=60.0)
    
    district = StringField('District', 
                           validators=[DataRequired()], 
                           default='Davanagere') # Example default
    
    season = SelectField('Season', 
                         choices=[
                             ('Kharif', 'Kharif'),
                             ('Rabi', 'Rabi'),
                             ('Summer', 'Summer'),
                             ('Whole Year', 'Whole Year')
                         ], 
                         validators=[DataRequired()])
    
    submit = SubmitField('Get Recommendations')

class PricePredictionForm(FlaskForm):
    """
    Form for a farmer to get a specific price prediction.
    """
    # We'll populate these dropdowns from the route
    crop = SelectField('Select Crop', validators=[DataRequired()])
    district = SelectField('Select District', validators=[DataRequired()])
    
    submit = SubmitField('Predict Price')
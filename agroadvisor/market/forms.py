from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class ProductForm(FlaskForm):
    """
    Form for a farmer to add or edit a product.
    """
    name = StringField('Product Name', 
                       validators=[DataRequired(), Length(min=2, max=100)])
    
    description = TextAreaField('Description', 
                                validators=[Length(max=500)])
    
    price = FloatField('Price (Rs.)', 
                       validators=[DataRequired(), NumberRange(min=0, message='Price must be positive.')])
    
    quantity = StringField('Quantity (e.g., "50 kg", "10 Quintal")', 
                           validators=[DataRequired(), Length(min=1, max=50)])
    
    contact_phone = StringField('Contact Phone (Optional)',
                                validators=[Length(min=10, max=20)])
    
    submit = SubmitField('List Product')
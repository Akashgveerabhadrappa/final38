from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from agroadvisor.extensions import db
from agroadvisor.models import Product, User  # Make sure User and Product are imported
from .forms import ProductForm

# Tell the blueprint where to find its templates
market_bp = Blueprint('market', __name__, template_folder='../templates/market')

@market_bp.route('/')
def marketplace():
    """
    Shows all products from all farmers. This is a public page.
    """
    # *** MODIFIED QUERY ***
    # We now also select User.id to create the seller detail link
    products = db.session.query(Product, User.username, User.id)\
        .join(User, Product.user_id == User.id)\
        .order_by(Product.date_posted.desc())\
        .all()
        
    return render_template('marketplace.html', title='Marketplace', products=products)


@market_bp.route('/add', methods=['GET', 'POST'])
@login_required  # Only logged-in users can add products
def add_product():
    """
    Farmers can add a new product to the market.
    """
    form = ProductForm()
    
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            quantity=form.quantity.data,
            contact_phone=form.contact_phone.data,
            user_id=current_user.id  # Link product to the logged-in user
        )
        db.session.add(product)
        db.session.commit()
        
        flash('Your product has been listed on the marketplace!', 'success')
        return redirect(url_for('market.marketplace'))
        
    return render_template('add_product.html', title='Add Product', form=form)


# *** NEW ROUTE ***
@market_bp.route('/seller/<int:user_id>')
@login_required
def seller_detail(user_id):
    """
    Shows a seller's profile and their other listings.
    """
    # Find the seller by their ID
    seller = User.query.get_or_404(user_id)
    
    # Find all products by that seller
    products = Product.query.filter_by(user_id=seller.id).order_by(Product.date_posted.desc()).all()
    
    return render_template('market/seller_detail.html', 
                           title=f"Profile: {seller.username}", 
                           seller=seller, 
                           products=products)
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
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
        
    # We re-use this template for both "Add" and "Update"
    # So we pass the title variable
    return render_template('add_product.html', title='Add Product', form=form)


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
    
    return render_template('seller_detail.html', 
                           title=f"Profile: {seller.username}", 
                           seller=seller, 
                           products=products)

#
# --- NEW ROUTE 1: UPDATE PRODUCT ---
#
@market_bp.route('/product/<int:product_id>/update', methods=['GET', 'POST'])
@login_required
def update_product(product_id):
    """
    Allows a farmer to edit one of their own products.
    """
    product = Product.query.get_or_404(product_id)
    
    # *** SECURITY CHECK ***
    # Ensure the logged-in user is the owner of the product
    if product.farmer.id != current_user.id:
        abort(403)  # 403 Forbidden
        
    form = ProductForm()
    
    if form.validate_on_submit():
        # Update the product's fields
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.quantity = form.quantity.data
        product.contact_phone = form.contact_phone.data
        db.session.commit() # No need to add, just commit the changes
        
        flash('Your product has been updated!', 'success')
        # Redirect back to their seller page
        return redirect(url_for('market.seller_detail', user_id=current_user.id))
        
    elif request.method == 'GET':
        # Pre-populate the form with the product's current data
        form.name.data = product.name
        form.description.data = product.description
        form.price.data = product.price
        form.quantity.data = product.quantity
        form.contact_phone.data = product.contact_phone
        
    # We re-use the 'add_product.html' template for the edit form
    return render_template('add_product.html', title='Update Product', form=form)


#
# --- NEW ROUTE 2: DELETE PRODUCT ---
#
@market_bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    """
    Allows a farmer to delete one of their own products.
    This route only accepts POST requests for security.
    """
    product = Product.query.get_or_404(product_id)
    
    # *** SECURITY CHECK ***
    if product.farmer.id != current_user.id:
        abort(403)
        
    db.session.delete(product)
    db.session.commit()
    
    flash('Your product has been deleted.', 'success')
    return redirect(url_for('market.seller_detail', user_id=current_user.id))
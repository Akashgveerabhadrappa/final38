from flask import Blueprint, render_template, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from functools import wraps
from agroadvisor.extensions import db
from agroadvisor.models import Product, User

# Tell the blueprint where to find its templates
admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')

# --- This is our custom decorator ---
def admin_required(f):
    """
    Restricts access to a route to users with the 'Admin' role.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required  # First, must be logged in
@admin_required  # Second, must be an admin
def dashboard():
    """
    Main admin dashboard. Only users with the 'Admin' role can see this.
    """
    # Fetch all users to display them
    users = User.query.order_by(User.id).all()
    return render_template('dashboard.html', title='Admin Dashboard', users=users)

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """
    Allows admin to delete a user.
    """
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    user_to_delete = User.query.get_or_404(user_id)
    
    # We must delete their products first (or set them to null)
    # This cascade depends on your DB setup, but explicit is safer.
    Product.query.filter_by(user_id=user_to_delete.id).delete()
    
    db.session.delete(user_to_delete)
    db.session.commit()
    
    flash(f'User {user_to_delete.username} and all their products have been deleted.', 'success')
    return redirect(url_for('admin.dashboard'))
from agroadvisor.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

class Role(db.Model):
    """
    Role model to differentiate between 'Farmer' and 'Admin'.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # This 'backref' gives us a 'user.role' attribute
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    """
    User model for authentication and farmer data.
    UserMixin adds required attributes for Flask-Login.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    
    # Foreign key relationship for role
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    
    # This 'backref' gives us a 'product.farmer' attribute
    products = db.relationship('Product', backref='farmer', lazy='dynamic')

    def set_password(self, password):
        """Hashes and sets the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Helper function to check if user is an admin."""
        return self.role and self.role.name == 'Admin'

    def __repr__(self):
        return f'<User {self.username}>'

class Product(db.Model):
    """
    Product model for the marketplace.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.String(50), nullable=False, default='1') # e.g., "50 kg"
    contact_phone = db.Column(db.String(20), nullable=True) # Optional phone #
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    # Foreign key to link product to a user (the farmer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Product {self.name}>'
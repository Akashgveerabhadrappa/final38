from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Create database instance
db = SQLAlchemy()

# Create migration engine instance
migrate = Migrate()

# Create login manager instance
login_manager = LoginManager()

# This tells Flask-Login which blueprint/route handles logging in
# 'auth.login' means the 'login' function inside the 'auth' blueprint
login_manager.login_view = 'auth.login'

# This is the message that will be flashed when a user tries to 
# access a page they need to be logged in for.
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info' # Bootstrap category
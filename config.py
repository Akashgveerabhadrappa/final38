import os
from dotenv import load_dotenv

# Find the absolute path of the root directory
basedir = os.path.abspath(os.path.dirname(__file__))
# Load environment variables from .env file
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Base configuration class."""
    
    # A secret key is required for sessions, forms (CSRF), and flash messages
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-hard-to-guess-default-key'
    
    # Database configuration
    # We use a simple SQLite database for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    
    # This disables an unneeded feature, saving resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False
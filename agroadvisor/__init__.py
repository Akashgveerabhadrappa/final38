from flask import Flask, render_template
from config import Config
from .extensions import db, login_manager, migrate
from .models import User, Role  # Import models
import os

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    
    # 1. Load configuration from config.py
    app.config.from_object(config_class)

    # 2. Ensure the instance folder exists (for our SQLite db)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # 3. Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        """Required callback for Flask-Login to load a user from session."""
        return User.query.get(int(user_id))

    # --- Register Blueprints ---
    # (We create the blueprint files in later phases)
    
    from .main.routes import main_bp
    app.register_blueprint(main_bp)

    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .farmer.routes import farmer_bp
    app.register_blueprint(farmer_bp, url_prefix='/farmer')

    from .admin.routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from .market.routes import market_bp
    app.register_blueprint(market_bp, url_prefix='/market')

    # --- End of Blueprint Registration ---

    # --- Create DB and Default Roles ---
    # This block runs within the app context to interact with the DB
    with app.app_context():
        # Create all database tables if they don't exist
        db.create_all()  
        
        # Create user roles if they don't exist
        if not Role.query.filter_by(name='Farmer').first():
            db.session.add(Role(name='Farmer'))
        if not Role.query.filter_by(name='Admin').first():
            db.session.add(Role(name='Admin'))
        
        db.session.commit()
    


    # ... (inside the create_app function)

    # --- Error Handlers ---
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # We also log the error to our file
        from agroadvisor.ml_models.utils import log_exception
        log_exception("Unhandled 500 Error", e)
        return render_template('500.html'), 500

    # --- Create DB and Default Roles ---
    # (This section is already here)
    with app.app_context():
        db.create_all()  
        # ... (rest of the code) ...
        db.session.commit()

    return app
from flask import Flask
import os

# Import configuration and utility functions/modules
import config
from database import init_db
from gemini_utils import configure_gemini_api, get_available_models
from config import ensure_allowed_context_dir

# Import Blueprints
from routes.main_routes import main_bp
from routes.context_routes import context_bp
from routes.pdf_routes import pdf_bp

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__, template_folder='templates') # Keep template folder at root

    # Load configuration from config.py
    app.config.from_object(config)
    # Optionally load instance-specific config if needed
    # app.config.from_pyfile('instance/config.py', silent=True)

    # --- Initialization ---
    print("Initializing application components...")

    # 1. Ensure allowed context directory exists
    if not ensure_allowed_context_dir():
        # Decide how critical this is. Maybe log warning and continue,
        # or raise an error if context features are essential.
        print("Warning: Failed to create or access the allowed context directory.")

    # 2. Initialize Database
    try:
        with app.app_context(): # Need app context for DB operations if they use Flask-SQLAlchemy etc.
                               # Not strictly needed for our current sqlite3 setup, but good practice.
            init_db()
    except Exception as e:
        print(f"Error initializing database: {e}")
        # Decide if the app can run without the DB. Probably not.
        raise RuntimeError(f"Failed to initialize database: {e}")

    # 3. Configure Gemini API
    if not configure_gemini_api():
        # App might still function without API key for some parts, but core chat won't work.
        print("Warning: Gemini API could not be configured. Chat features will be unavailable.")
        # Optionally, disable related routes or features here.
    else:
        # Pre-fetch models on startup to populate cache
        print("Pre-fetching available Gemini models...")
        get_available_models(force_refresh=True)


    # --- Register Blueprints ---
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(context_bp, url_prefix='/context') # Add prefix for context routes
    app.register_blueprint(pdf_bp, url_prefix='/pdf')       # Add prefix for pdf routes

    print("Blueprints registered.")
    print(f"App ready. Running in {'Debug' if app.debug else 'Production'} mode.")
    print(f"Access at: http://{config.HOST}:{config.PORT}")

    return app

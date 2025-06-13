from flask import Flask
import os

# Import configuration and utility functions/modules
import config
from database import init_db
from gemini_utils import configure_client, get_available_models # Renamed here
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
    if not app.config.get('TESTING'):
        print("Initializing application components...")

    # 1. Ensure allowed context directory exists
    if not ensure_allowed_context_dir():
        # Decide how critical this is. Maybe log warning and continue,
        # or raise an error if context features are essential.
        print("Warning: Failed to create or access the allowed context directory.")

    # 2. Initialize Database
    # In testing, the app fixture in conftest.py handles DB initialization.
    if not app.config.get('TESTING'):
        try:
            with app.app_context():
                init_db()
        except Exception as e:
            print(f"Error initializing database: {e}")
            # Decide if the app can run without the DB. Probably not.
            raise RuntimeError(f"Failed to initialize database: {e}")

    # 3. Configure Gemini API
    # In testing, API calls should ideally be mocked.
    # Do not configure real Gemini client during app creation for tests.
    # Test fixtures (like mock_gemini_client) or specific test setups
    # will be responsible for initializing/mocking gemini_utils.client.
    if not app.config.get('TESTING'):
        if not configure_client(): # Renamed here
            print("Warning: Gemini API could not be configured. Chat features will be unavailable.")
        else:
            print("Pre-fetching available Gemini models...")
            get_available_models(force_refresh=True)
    # else:
        # For testing, client is configured by test fixtures.
        # The app() fixture in conftest.py ensures GOOGLE_API_KEY is patched in config
        # and gemini_utils module for tests that might need to call configure_client() directly.
        # No need to call configure_client() here during app setup for tests.
        # We also don't pre-fetch models during testing to avoid actual API calls.
        # pass


    # --- Register Blueprints ---
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(context_bp, url_prefix='/context') # Add prefix for context routes
    app.register_blueprint(pdf_bp, url_prefix='/pdf')       # Add prefix for pdf routes

    if not app.config.get('TESTING'):
        print("Blueprints registered.")
        print(f"App ready. Running in {'Debug' if app.debug else 'Production'} mode.")
        print(f"Access at: http://{config.HOST}:{config.PORT}")
    else:
        # In testing, we might still want to know blueprints are registered.
        print("Blueprints registered.")


    return app

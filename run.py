from app_factory import create_app
from config import HOST, PORT, DEBUG_MODE

# Create the Flask app instance using the factory
app = create_app()

if __name__ == '__main__':
    # Run the Flask development server
    # Debug mode and host/port settings are loaded from config via app.config
    # but we can also pass them explicitly to app.run() if needed,
    # though it's generally better to rely on the config loaded by create_app.
    print(f"Starting server with debug={DEBUG_MODE}, host={HOST}, port={PORT}")
    app.run(debug=DEBUG_MODE, host=HOST, port=PORT)

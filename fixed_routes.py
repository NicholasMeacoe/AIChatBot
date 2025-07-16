# Add these routes BEFORE the if __name__ == '__main__': block

@app.route('/clean')
def clean_interface():
    """Serve the clean version of the chat interface."""
    return render_template('clean_index.html', 
                          available_models=FETCHED_MODELS,
                          default_model=DEFAULT_MODEL_NAME)

@app.route('/minimal')
def minimal_interface():
    """Serve the minimal version of the chat interface."""
    return render_template('minimal.html', 
                          available_models=FETCHED_MODELS,
                          default_model=DEFAULT_MODEL_NAME)

@app.route('/simple')
def simple_interface():
    """Serve the simple version of the chat interface."""
    return render_template('simple.html')

@app.route('/test-route')
def test_simple_route():
    """A simple test route."""
    return "Test route is working!"

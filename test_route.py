from flask import render_template, Blueprint

test_bp = Blueprint('test', __name__)

@test_bp.route('/test_chat')
def test_chat():
    """Serve a simple test chat interface."""
    return render_template('test_chat.html')

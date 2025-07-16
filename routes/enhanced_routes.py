from flask import Blueprint, request, jsonify, send_file, Response
from features.multimodal import MultiModalProcessor
from features.templates import TemplateManager
from features.export import ExportManager
from features.search import SearchManager
from features.code_execution import CodeExecutor
from features.plugins import PluginManager
from features.smart_context import SmartContextManager
from features.voice import VoiceInterface
from features.analytics import AnalyticsManager
import json
import tempfile
import os

enhanced_bp = Blueprint('enhanced', __name__)

# Initialize feature managers (with error handling)
try:
    multimodal = MultiModalProcessor()
except Exception as e:
    print(f"Warning: MultiModal processor failed to initialize: {e}")
    multimodal = None

templates = TemplateManager()
code_executor = CodeExecutor()
plugin_manager = PluginManager()
voice_interface = VoiceInterface()

@enhanced_bp.route('/multimodal/process', methods=['POST'])
def process_multimodal_file():
    """Process multimodal files (images, audio, video)"""
    try:
        if multimodal is None:
            return jsonify({'error': 'Multimodal processing not available'}), 503
            
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            file.save(temp_file.name)
            result = multimodal.process_file(temp_file.name)
            
        # Delete file after processing
        try:
            os.unlink(temp_file.name)
        except PermissionError:
            pass  # File will be cleaned up by system
        
        if result is None:
            return jsonify({'error': 'Unsupported file type'}), 400
            
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Multimodal processing error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@enhanced_bp.route('/templates', methods=['GET'])
def get_templates():
    """Get all templates or by category"""
    category = request.args.get('category')
    return jsonify(templates.get_templates(category))

@enhanced_bp.route('/templates', methods=['POST'])
def create_template():
    """Create new template"""
    data = request.json
    templates.add_template(
        data['id'], data['name'], data['category'], 
        data['template'], data['variables']
    )
    return jsonify({'success': True})

@enhanced_bp.route('/templates/<template_id>/apply', methods=['POST'])
def apply_template(template_id):
    """Apply template with variables"""
    variables = request.json
    result = templates.apply_template(template_id, variables)
    return jsonify({'result': result})

@enhanced_bp.route('/export/<format_type>')
def export_conversation(format_type):
    """Export conversation in specified format"""
    from database import get_db
    export_manager = ExportManager(get_db())
    
    conversation_id = request.args.get('conversation_id')
    content = export_manager.export_conversation(conversation_id, format_type)
    
    if format_type == 'json':
        return Response(content, mimetype='application/json')
    elif format_type == 'html':
        return Response(content, mimetype='text/html')
    else:  # markdown
        return Response(content, mimetype='text/plain')

@enhanced_bp.route('/share/<conversation_id>', methods=['POST'])
def create_share_link(conversation_id):
    """Create shareable link"""
    from database import get_db
    export_manager = ExportManager(get_db())
    share_id = export_manager.create_share_link(conversation_id)
    return jsonify({'share_id': share_id, 'url': f'/shared/{share_id}'})

@enhanced_bp.route('/search', methods=['GET'])
def search_messages():
    """Search messages"""
    from database import get_db
    search_manager = SearchManager(get_db())
    
    query = request.args.get('q')
    results = search_manager.search_messages(query)
    return jsonify([dict(row) for row in results])

@enhanced_bp.route('/tags', methods=['GET', 'POST'])
def manage_tags():
    """Get or add tags"""
    from database import get_db
    search_manager = SearchManager(get_db())
    
    if request.method == 'GET':
        conversation_id = request.args.get('conversation_id')
        tags = search_manager.get_tags(conversation_id)
        return jsonify([dict(row) for row in tags])
    else:
        data = request.json
        search_manager.add_tag(data['conversation_id'], data['tag'])
        return jsonify({'success': True})

@enhanced_bp.route('/execute', methods=['POST'])
def execute_code():
    """Execute code"""
    data = request.json
    result = code_executor.execute_code(
        data['code'], 
        data.get('language', 'python'),
        data.get('context_files')
    )
    return jsonify(result)

@enhanced_bp.route('/plugins', methods=['GET'])
def list_plugins():
    """List available plugins"""
    return jsonify(plugin_manager.list_plugins())

@enhanced_bp.route('/plugins/<plugin_name>/execute', methods=['POST'])
def execute_plugin(plugin_name):
    """Execute plugin"""
    data = request.json
    result = plugin_manager.execute_plugin(plugin_name, **data)
    return jsonify(result)

@enhanced_bp.route('/context/suggest', methods=['POST'])
def suggest_context():
    """Get smart context suggestions"""
    from config import GOOGLE_API_KEY, ALLOWED_CONTEXT_DIR
    smart_context = SmartContextManager(GOOGLE_API_KEY, ALLOWED_CONTEXT_DIR)
    
    data = request.json
    suggestions = smart_context.analyze_conversation_for_context(data['conversation'])
    return jsonify(suggestions)

@enhanced_bp.route('/voice/speech-to-text', methods=['POST'])
def speech_to_text():
    """Convert speech to text"""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        audio_file.save(temp_file.name)
        result = voice_interface.speech_to_text(audio_file=temp_file.name)
        os.unlink(temp_file.name)
    
    return jsonify(result)

@enhanced_bp.route('/voice/text-to-speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech"""
    data = request.json
    text = data.get('text', '')
    
    audio_file = voice_interface.create_audio_response(text)
    if audio_file:
        return send_file(audio_file, as_attachment=True, download_name='response.wav')
    
    return jsonify({'error': 'Failed to generate audio'}), 500

@enhanced_bp.route('/analytics/usage')
def get_usage_analytics():
    """Get usage analytics"""
    from database import get_db
    analytics = AnalyticsManager(get_db())
    
    days = int(request.args.get('days', 30))
    stats = analytics.get_usage_stats(days)
    return jsonify(stats)

@enhanced_bp.route('/analytics/insights')
def get_conversation_insights():
    """Get conversation insights"""
    from database import get_db
    analytics = AnalyticsManager(get_db())
    
    days = int(request.args.get('days', 30))
    insights = analytics.get_conversation_insights(days)
    return jsonify(insights)

@enhanced_bp.route('/analytics/productivity')
def get_productivity_metrics():
    """Get productivity metrics"""
    from database import get_db
    analytics = AnalyticsManager(get_db())
    
    days = int(request.args.get('days', 30))
    metrics = analytics.get_productivity_metrics(days)
    return jsonify(metrics)
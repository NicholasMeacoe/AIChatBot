"""
Authentication Routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from oauth_auth import OAuth2Manager, admin_required
from user_management import UserManager
from auth_config import AuthConfig

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Initialize managers
oauth_manager = OAuth2Manager()
user_manager = UserManager()

@auth_bp.route('/login')
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html', 
                         provider=AuthConfig.OAUTH2_PROVIDER.title())

@auth_bp.route('/authorize')
def authorize():
    """Redirect to OAuth2 provider"""
    try:
        return oauth_manager.get_authorization_url()
    except Exception as e:
        flash(f'Authentication error: {str(e)}', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/callback')
def callback():
    """Handle OAuth2 callback"""
    user, error = oauth_manager.handle_callback()
    
    if error:
        flash(f'Authentication failed: {error}', 'error')
        return redirect(url_for('auth.login'))
    
    if user:
        login_user(user, remember=True)
        flash(f'Welcome, {user.name}!', 'success')
        
        # Redirect to next page or home
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.index'))
    
    flash('Authentication failed. Please try again.', 'error')
    return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    user_name = current_user.name
    logout_user()
    oauth_manager.logout_user()
    flash(f'Goodbye, {user_name}!', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/admin')
@admin_required
def admin_panel():
    """Admin panel"""
    users = user_manager.get_all_users()
    return render_template('auth/admin.html', users=users)

@auth_bp.route('/admin/users/<user_id>/role', methods=['POST'])
@admin_required
def update_user_role():
    """Update user role (AJAX endpoint)"""
    data = request.get_json()
    user_id = data.get('user_id')
    new_role = data.get('role')
    
    if not user_id or not new_role:
        return jsonify({'error': 'Missing user_id or role'}), 400
    
    if new_role not in ['user', 'admin']:
        return jsonify({'error': 'Invalid role'}), 400
    
    try:
        user_manager.update_user_role(user_id, new_role)
        return jsonify({'success': True, 'message': 'User role updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/admin/users/<user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(user_id):
    """Deactivate user"""
    try:
        user_manager.deactivate_user(user_id)
        flash('User deactivated successfully', 'success')
    except Exception as e:
        flash(f'Error deactivating user: {str(e)}', 'error')
    
    return redirect(url_for('auth.admin_panel'))

@auth_bp.route('/status')
def auth_status():
    """Get authentication status (API endpoint)"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'name': current_user.name,
                'email': current_user.email,
                'role': current_user.role,
                'request_count': current_user.request_count,
                'can_make_request': current_user.can_make_request()
            }
        })
    else:
        return jsonify({'authenticated': False})

# Error handlers
@auth_bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access"""
    if request.is_json:
        return jsonify({'error': 'Authentication required'}), 401
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('auth.login'))

@auth_bp.errorhandler(403)
def forbidden(error):
    """Handle forbidden access"""
    if request.is_json:
        return jsonify({'error': 'Access forbidden'}), 403
    flash('You do not have permission to access this resource.', 'error')
    return redirect(url_for('main.index'))

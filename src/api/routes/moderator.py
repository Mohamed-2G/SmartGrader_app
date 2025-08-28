from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from src.core.models import User, Exam, Submission, SystemSettings
from src.core.extensions import db, mail
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from datetime import datetime, timedelta
import json

moderator_bp = Blueprint('moderator', __name__)

serializer = URLSafeTimedSerializer('dev_key')  # Replace with app.config['SECRET_KEY'] in app factory

@moderator_bp.route('/moderator/dashboard')
@login_required
def dashboard():
    if current_user.role != 'moderator':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    total_users = User.query.count()
    total_exams = Exam.query.count()
    total_submissions = Submission.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    return render_template('moderator/dashboard.html', 
                         total_users=total_users,
                         total_exams=total_exams,
                         total_submissions=total_submissions,
                         recent_users=recent_users)

@moderator_bp.route('/moderator/users')
@login_required
def moderator_users():
    if current_user.role != 'moderator':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    users = User.query.order_by(User.created_at.desc()).all()
    now = datetime.utcnow()
    return render_template('moderator/users.html', users=users, now=now)

@moderator_bp.route('/moderator/send_reset/<int:user_id>', methods=['POST'])
@login_required
def send_password_reset(user_id):
    if current_user.role != 'moderator':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    user = User.query.get_or_404(user_id)
    if user.role not in ['student', 'instructor']:
        return jsonify({'success': False, 'error': 'Can only reset for students or instructors'}), 400
    token = serializer.dumps(user.email, salt='password-reset-salt')
    reset_url = url_for('reset_password', token=token, _external=True)
    try:
        msg = Message('SmartGrader Password Reset', recipients=[user.email])
        msg.body = f"Hello {user.username},\n\nA password reset was requested for your SmartGrader account. Click the link below to reset your password (valid for 1 hour):\n\n{reset_url}\n\nIf you did not request this, please ignore this email."
        mail.send(msg)
        return jsonify({'success': True, 'message': f'Reset link sent to {user.email}.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@moderator_bp.route('/moderator/user/<int:user_id>/suspend', methods=['POST'])
@login_required
def suspend_user(user_id):
    if current_user.role != 'moderator':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    user = User.query.get_or_404(user_id)
    days = int(request.form.get('days', 0))
    if days > 0:
        user.suspended_until = datetime.utcnow() + timedelta(days=days)
        user.is_active = False
    else:
        user.suspended_until = None
        user.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': f'User {user.username} suspended.'})

@moderator_bp.route('/moderator/user/<int:user_id>/unsuspend', methods=['POST'])
@login_required
def unsuspend_user(user_id):
    if current_user.role != 'moderator':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    user = User.query.get_or_404(user_id)
    user.suspended_until = None
    user.is_active = True
    db.session.commit()
    return jsonify({'success': True, 'message': f'User {user.username} unsuspended.'})

@moderator_bp.route('/moderator/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'moderator':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': f'User {user.username} deleted.'})

@moderator_bp.route('/moderator/user/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'moderator':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    user = User.query.get_or_404(user_id)
    data = request.form
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    user.language = data.get('language', user.language)
    if user.role != 'moderator':
        user.role = data.get('role', user.role)
    db.session.commit()
    return jsonify({'success': True, 'message': f'User {user.username} updated.'})

@moderator_bp.route('/moderator/system')
@login_required
def moderator_system():
    if current_user.role != 'moderator':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    # Load current settings from database
    settings = {}
    db_settings = SystemSettings.query.all()
    for setting in db_settings:
        settings[setting.setting_key] = setting.setting_value
    
    # Default values if settings don't exist
    default_settings = {
        'deepseek_model': 'deepseek-chat',
        'temperature': '0.3',
        'max_tokens': '1000',
        'grading_timeout': '30',
        'session_timeout': '60',
        'max_file_size': '10',
        'backup_frequency': 'weekly',
        'log_level': 'info',
        'require_strong_passwords': 'true',
        'enable_two_factor': 'true',
        'log_login_attempts': 'true',
        'enable_rate_limiting': 'true'
    }
    
    # Use database values or defaults
    for key, default_value in default_settings.items():
        if key not in settings:
            settings[key] = default_value
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    return render_template('moderator/system.html', last_updated=now, settings=settings)

@moderator_bp.route('/moderator/system/save_settings', methods=['POST'])
@login_required
def save_system_settings():
    if current_user.role != 'moderator':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        settings = data.get('settings', {})
        
        for key, value in settings.items():
            # Convert boolean values to string for storage
            if isinstance(value, bool):
                value = str(value).lower()
            else:
                value = str(value)
            
            # Check if setting exists
            existing_setting = SystemSettings.query.filter_by(setting_key=key).first()
            
            if existing_setting:
                # Update existing setting
                existing_setting.setting_value = value
                existing_setting.updated_at = datetime.utcnow()
                existing_setting.updated_by = current_user.id
            else:
                # Create new setting
                new_setting = SystemSettings(
                    setting_key=key,
                    setting_value=value,
                    setting_type='string',
                    updated_by=current_user.id
                )
                db.session.add(new_setting)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@moderator_bp.route('/moderator/system/confirm_settings', methods=['POST'])
@login_required
def confirm_system_settings():
    if current_user.role != 'moderator':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Here you could add additional logic to apply settings
        # For example, restart services, clear caches, etc.
        
        return jsonify({'success': True, 'message': 'Settings confirmed and applied successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

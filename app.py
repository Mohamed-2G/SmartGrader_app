"""
SmartGrader - AI-Powered Exam Grading System
Main Flask application with teacher and moderator interfaces
"""


from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import mimetypes
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
# Removed direct Message import (email sending disabled)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import openai
import os
import uuid
import requests
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import json
import time

from src.services.grader.prompt_builder import format_json_grading_prompt
from src.services.grader.exam_grader import ExamGrader

# Helper functions are imported as needed in specific routes

# Import config and extensions
from src.core.config import Config, DEEPSEEK_API_KEY
from src.core.extensions import db, mail, migrate, login_manager

# DeepSeek API configuration
if DEEPSEEK_API_KEY:
    print("DeepSeek API key found and ready to use")
else:
    print("Warning: DEEPSEEK_API_KEY not found in environment variables")






app = Flask(__name__)
app.config.from_object(Config)

# Configure session for better persistence
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # 30 days
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize extensions
db.init_app(app)
mail.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
login_manager.login_view = 'login'

from src.core.models import User, Message as UserMessage, UploadedExam, StudentSubmission, QuestionAnswer, SystemSettings
from src.utils.translations import get_text, get_language, set_language, get_languages, LANGUAGES, init_app

# Initialize translation system
init_app(app)

# Flask-Login user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to HTML line breaks"""
    if text is None:
        return ''
    from markupsafe import Markup
    return Markup(text.replace('\n', '<br>'))


# Context processor for translations
@app.context_processor
def inject_translations():
    return {
        'get_text': get_text,
        't': get_text,
        'get_language': get_language,
        'get_languages': get_languages,
        'LANGUAGES': LANGUAGES,
        'current_language': get_language()
    }

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'instructor':
            return redirect(url_for('instructor.dashboard'))
        elif current_user.role == 'moderator':
            return redirect(url_for('moderator.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        language = request.form.get('language', 'english')
        user = User.query.filter((User.username==identifier)|(User.email==identifier)).first()
        if user and check_password_hash(user.password_hash, password) and user.is_active:
            login_user(user)
            user.language = language
            db.session.commit()
            
            # Make session permanent and set language
            session.permanent = True
            session['language'] = language
            
            flash(get_text('login_successful', language), 'success')
            if user.role == 'instructor':
                return redirect(url_for('instructor.dashboard'))
            if user.role == 'moderator':
                return redirect(url_for('moderator.dashboard'))
            return redirect(url_for('student.dashboard'))
        else:
            flash(get_text('invalid_credentials', 'english'), 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    language = current_user.language if current_user.is_authenticated else 'english'
    flash(get_text('logout_successful', language), 'info')
    return redirect(url_for('index'))





# Note: Student and Instructor routes are now handled by blueprints in routes/student.py and routes/instructor.py

# Register blueprints
from src.api.routes.student import student_bp
from src.api.routes.instructor import instructor_bp
from src.api.routes.ai_grading import ai_grading_bp
# from src.api.routes.file_upload import file_upload_bp
from src.api.routes.auth import auth_bp
# Removed settings API in favor of moderator UI-only settings
from src.api.routes.moderator import moderator_bp

app.register_blueprint(student_bp)
app.register_blueprint(instructor_bp)
app.register_blueprint(ai_grading_bp)
# app.register_blueprint(file_upload_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(moderator_bp)

# Messaging Routes
@app.route('/messages')
@login_required
def messages():
    """Display user's messages (inbox and sent)"""
    # Get received messages
    received_messages = UserMessage.query.filter_by(recipient_id=current_user.id).order_by(UserMessage.sent_at.desc()).all()
    
    # Get sent messages
    sent_messages = UserMessage.query.filter_by(sender_id=current_user.id).order_by(UserMessage.sent_at.desc()).all()
    
    return render_template('messages.html', 
                         received_messages=received_messages, 
                         sent_messages=sent_messages)

@app.route('/compose_message', methods=['GET', 'POST'])
@login_required
def compose_message():
    """Compose and send a new message"""
    if request.method == 'POST':
        recipient_username = request.form.get('recipient')
        subject = request.form.get('subject', '')
        content = request.form.get('content')
        
        if not content:
            flash('Message content is required.', 'error')
            return redirect(url_for('compose_message'))
        
        # Find recipient by username
        recipient = User.query.filter_by(username=recipient_username).first()
        if not recipient:
            flash('Recipient not found.', 'error')
            return redirect(url_for('compose_message'))
        
        # Create and save message
        message = UserMessage(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            subject=subject,
            content=content
        )
        
        try:
            db.session.add(message)
            db.session.commit()
            flash('Message sent successfully!', 'success')
            return redirect(url_for('messages'))
        except Exception as e:
            db.session.rollback()
            flash('Error sending message. Please try again.', 'error')
            return redirect(url_for('compose_message'))
    
    # GET request - show compose form
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('compose_message.html', users=users)

@app.route('/messages/<int:message_id>')
@login_required
def view_message(message_id):
    """View a specific message"""
    message = UserMessage.query.get_or_404(message_id)
    
    # Check if user is sender or recipient
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        flash('You do not have permission to view this message.', 'error')
        return redirect(url_for('messages'))
    
    # Mark as read if user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        db.session.commit()
    
    return render_template('view_message.html', message=message)

@app.route('/api/unread_messages_count')
@login_required
def unread_messages_count():
    """API endpoint to get count of unread messages"""
    count = UserMessage.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/mark_all_messages_read', methods=['POST'])
@login_required
def mark_all_messages_read():
    """API endpoint to mark all messages as read"""
    try:
        unread_messages = UserMessage.query.filter_by(recipient_id=current_user.id, is_read=False).all()
        for message in unread_messages:
            message.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Migration command removed - all files are now stored directly in database BLOBs

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Handle both form data and JSON data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        username = data.get('username')
        email = data.get('email')
        name = data.get('name', '')  # Full name from signup form
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        language = data.get('language', 'english')
        security_question = data.get('security_question')
        security_answer = data.get('security_answer')
        
        # Validation
        if not all([username, email, password, confirm_password, security_question, security_answer]):
            if request.is_json:
                return jsonify({'success': False, 'error': 'All required fields must be filled'})
            flash('All required fields must be filled.', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Passwords do not match'})
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Password must be at least 8 characters long'})
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('register'))
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Username or email already exists'})
            flash('Username or email already exists.', 'error')
            return redirect(url_for('register'))
        
        try:
            # Create new user
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role='student',  # All new users are students by default
                language=language,
                security_question=security_question,
                security_answer=security_answer
            )
            
            # Add name to bio field if provided
            if name:
                user.bio = f"Name: {name}"
            
            db.session.add(user)
            db.session.commit()
            
            # Set session language for new users
            session.permanent = True
            session['language'] = language
            
            # Send welcome email
            # try:
            #     msg = Message('Welcome to SmartGrader!', recipients=[email])
            #     msg.body = f"""Hello {name or username},
            #
            # Welcome to SmartGrader! Your account has been created successfully.
            #
            # Your login credentials:
            # Username: {username}
            # Email: {email}
            #
            # You can now log in to your account and start using SmartGrader.
            #
            # Best regards,
            # The SmartGrader Team"""
            #     mail.send(msg)
            # except Exception as e:
            #     print(f"Error sending welcome email: {e}")
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Registration successful! Please check your email.'})
            
            flash('Registration successful! Please check your email.', 'success')
            return redirect(url_for('login'))
            
        except IntegrityError:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'error': 'Username or email already exists'})
            flash('Username or email already exists.', 'error')
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)})
            flash(f'Error: {str(e)}', 'error')
    
    # GET request - show registration page (for direct access)
    languages = [
        ('english', 'English'),
        ('french', 'French'),
        ('arabic', 'Arabic'),
        ('turkish', 'Turkish'),
    ]
    return render_template('register.html', languages=languages)



# Create database tables and default users
def create_tables_and_default_users():
    """Create database tables and default users if they don't exist"""
    db.create_all()
    
    # Default users info
    defaults = [
        {
            'role': 'moderator',
            'username': 'admin',
            'email': 'moderator@smartgrader.com',
            'password': 'admin12',
            'security_question': 'What is your favorite color?',
            'security_answer': 'blue',
        },
        {
            'role': 'instructor',
            'username': 'teacher',
            'email': 'teacher@smartgrader.com',
            'password': 'teacher12',
            'security_question': 'What is your favorite color?',
            'security_answer': 'green',
        },
        {
            'role': 'student',
            'username': 'student',
            'email': 'student@smartgrader.com',
            'password': 'student12',
            'security_question': 'What is your favorite color?',
            'security_answer': 'red',
        },
    ]
    
    for user_info in defaults:
        # Check if this specific user already exists (by username or email)
        existing_user = User.query.filter(
            (User.username == user_info['username']) | 
            (User.email == user_info['email'])
        ).first()
        
        if not existing_user:
            new_user = User(
                username=user_info['username'],
                email=user_info['email'],
                password_hash=generate_password_hash(user_info['password']),
                role=user_info['role'],
                language='english',
                is_active=True,
                security_question=user_info['security_question'],
                security_answer=user_info['security_answer']
            )
            db.session.add(new_user)
            try:
                db.session.commit()
                print(f"Default {user_info['role']} created: username='{user_info['username']}', password='{user_info['password']}'")
            except IntegrityError:
                db.session.rollback()
                print(f"Error creating {user_info['role']}: User already exists")
        else:
            print(f"Default {user_info['role']} already exists (username: {user_info['username']})")


if __name__ == '__main__':
    with app.app_context():
        create_tables_and_default_users()
    app.run(debug=True)
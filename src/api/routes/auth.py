"""
Authentication Routes
Handles login, logout, and registration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
import requests
import os
import secrets
import string
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.core.models import User, Message as UserMessage, db
from src.core.config import SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT
from src.utils.translations import get_text

# Create Blueprint
auth_bp = Blueprint('auth', __name__)

# Available languages (codes)
languages = ['en', 'fr', 'ar', 'tr']

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def generate_reset_token():
    """Generate a secure reset token"""
    return secrets.token_urlsafe(32)

def send_verification_email(email, code, token, language='english'):
    """Send verification code email with reset link"""
    try:
        # Email configuration
        smtp_server = SMTP_SERVER
        smtp_port = SMTP_PORT
        sender_email = SMTP_EMAIL
        sender_password = SMTP_PASSWORD
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = get_text('verification_email_subject', language)
        
        # Generate reset link
        reset_link = url_for('auth.verify_code', email=email, token=token, _external=True)
        
        # Email body (plain text)
        body = f"""
        {get_text('verification_email_greeting', language)}
        
        {get_text('verification_email_body', language)}
        
        {get_text('verification_code', language)}: {code}
        
        {get_text('verification_email_expiry', language)}
        
        {get_text('verification_email_link_text', language)}: {reset_link}
        
        {get_text('verification_email_footer', language)}
        """
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .code {{ background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SmartGrader</h1>
                    <p>{get_text('verification_email_subject', language)}</p>
                </div>
                <div class="content">
                    <p><strong>{get_text('verification_email_greeting', language)}</strong></p>
                    
                    <p>{get_text('verification_email_body', language)}</p>
                    
                    <div class="code">{code}</div>
                    
                    <p><em>{get_text('verification_email_expiry', language)}</em></p>
                    
                    <p><strong>{get_text('verification_email_link_text', language)}:</strong></p>
                    <a href="{reset_link}" class="button">{get_text('verification_email_link_text', language)}</a>
                    
                    <div class="footer">
                        <p>{get_text('verification_email_footer', language)}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Attach both plain text and HTML versions
        msg.attach(MIMEText(body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        if smtp_password and smtp_password.strip():  # Only send if SMTP is properly configured
            try:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                server.quit()
                print(f"✅ Email sent successfully to {email}")
                return True
            except Exception as smtp_error:
                print(f"❌ SMTP Error: {smtp_error}")
                return False
        else:
            # For development, just print the code and link
            print("=" * 60)
            print("📧 DEVELOPMENT MODE - EMAIL NOT SENT")
            print("=" * 60)
            print(f"📧 To: {email}")
            print(f"📧 Subject: {get_text('verification_email_subject', language)}")
            print(f"🔐 Verification Code: {code}")
            print(f"🔗 Reset Link: {reset_link}")
            print("=" * 60)
            print("💡 To enable real email sending, configure SMTP settings in .env file")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"❌ Error in send_verification_email: {e}")
        return False

def send_moderator_request_email(user, reason, language='english'):
    """Send moderator request email"""
    try:
        # Find moderators
        moderators = User.query.filter_by(role='moderator').all()
        
        for moderator in moderators:
            # Create message in database
            message = UserMessage(
                sender_id=user.id,
                recipient_id=moderator.id,
                subject=get_text('password_reset_request', language),
                content=f"""
                {get_text('password_reset_request_body', language)}
                
                {get_text('user_details', language)}:
                - {get_text('username', language)}: {user.username}
                - {get_text('email_address', language)}: {user.email}
                
                {get_text('reset_reason', language)}: {reason}
                
                {get_text('moderator_action_required', language)}
                """,
                sent_at=datetime.utcnow(),
                is_read=False,
                message_type='system'
            )
            db.session.add(message)
        
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Error sending moderator request: {e}")
        return False

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # Can be username or email
        password = request.form.get('password')
        
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(get_text('login_successful', user.language), 'success')
            return redirect(url_for('index'))
        else:
            flash(get_text('invalid_credentials', 'english'), 'error')
    
    return render_template('login.html', languages=languages)

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash(get_text('logout_successful', 'english'), 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_language', methods=['POST'])
def change_language():
    """Change user language preference (accepts JSON or form) and returns JSON.
    Accepts both codes (en, fr, ar, tr) and names (english, french, arabic, turkish).
    """
    try:
        name_to_code = {
            'english': 'en', 'en': 'en',
            'french': 'fr', 'fr': 'fr',
            'arabic': 'ar', 'ar': 'ar',
            'turkish': 'tr', 'tr': 'tr',
        }

        language = None
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            language = payload.get('language')
        if not language:
            language = request.form.get('language')

        code = name_to_code.get((language or '').strip().lower())
        if not code:
            return jsonify({'success': False, 'error': 'Invalid language'}), 400

        # Persist preference on both the user (if logged in) and the session
        if current_user.is_authenticated:
            current_user.language = code
            db.session.commit()
        session['language'] = code

        return jsonify({'success': True, 'language': code})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Handle password reset request via security question"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash(get_text('email_not_found', 'english'), 'error')
            return render_template('forgot_password.html')
        
        if not user.security_question or not user.security_answer:
            flash('No security question found for this account. Please contact an administrator.', 'error')
            return render_template('forgot_password.html')
        
        # Redirect to security question page
        return redirect(url_for('auth.answer_security_question', email=email))
    
    return render_template('forgot_password.html')

@auth_bp.route('/answer_security_question', methods=['GET', 'POST'])
def answer_security_question():
    """Handle security question verification"""
    email = request.args.get('email') or request.form.get('email')
    
    if not email:
        flash(get_text('invalid_request', 'english'), 'error')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash(get_text('email_not_found', 'english'), 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if not user.security_question or not user.security_answer:
        flash('No security question found for this account. Please contact an administrator.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        security_answer = request.form.get('security_answer')
        
        if not security_answer:
            flash(get_text('security_answer_required', user.language), 'error')
            return render_template('answer_security_question.html', user=user, email=email)
        
        # Check if answer matches (case-insensitive)
        if security_answer.lower().strip() == user.security_answer.lower().strip():
            # Generate reset token
            token = generate_reset_token()
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            flash(get_text('security_question_success', user.language), 'success')
            return redirect(url_for('auth.change_password', email=email, token=token))
        else:
            flash(get_text('security_question_incorrect', user.language), 'error')
    
    return render_template('answer_security_question.html', user=user, email=email)

@auth_bp.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    """Handle verification code verification"""
    email = request.args.get('email') or request.form.get('email')
    token = request.args.get('token') or request.form.get('token')
    
    if not email or not token:
        flash(get_text('invalid_request', 'english'), 'error')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.filter_by(email=email, reset_token=token).first()
    
    if not user or user.reset_token_expires < datetime.utcnow():
        flash(get_text('invalid_or_expired_token', 'english'), 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        verification_code = request.form.get('verification_code')
        
        if user.reset_code == verification_code and user.reset_code_expires > datetime.utcnow():
            # Code is valid, redirect to password change
            return redirect(url_for('auth.change_password', email=email, token=token))
        else:
            flash(get_text('invalid_or_expired_code', user.language), 'error')
    
    return render_template('verify_code.html', email=email, token=token)

@auth_bp.route('/resend_code', methods=['POST'])
def resend_code():
    """Resend verification code"""
    email = request.form.get('email')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash(get_text('email_not_found', 'english'), 'error')
        return redirect(url_for('auth.forgot_password'))
    
    # Generate new code
    code = generate_verification_code()
    user.reset_code = code
    user.reset_code_expires = datetime.utcnow() + timedelta(minutes=15)
    
    db.session.commit()
    
    # Send new email
    if send_verification_email(email, code, user.reset_token, user.language):
        flash(get_text('code_resent', user.language), 'success')
    else:
        flash(get_text('email_send_error', user.language), 'error')
    
    return redirect(url_for('auth.verify_code', email=email, token=user.reset_token))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    """Handle password change after verification"""
    email = request.args.get('email') or request.form.get('email')
    token = request.args.get('token') or request.form.get('token')
    
    if not email or not token:
        flash(get_text('invalid_request', 'english'), 'error')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.filter_by(email=email, reset_token=token).first()
    
    if not user or user.reset_token_expires < datetime.utcnow():
        flash(get_text('invalid_or_expired_token', 'english'), 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if len(new_password) < 8:
            flash(get_text('password_too_short', user.language), 'error')
        elif new_password != confirm_password:
            flash(get_text('passwords_not_match', user.language), 'error')
        else:
            # Update password
            user.password_hash = generate_password_hash(new_password)
            
            # Clear reset fields
            user.reset_token = None
            user.reset_token_expires = None
            user.reset_code = None
            user.reset_code_expires = None
            
            db.session.commit()
            
            flash(get_text('password_updated_successfully', user.language), 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('change_password.html', email=email, token=token)



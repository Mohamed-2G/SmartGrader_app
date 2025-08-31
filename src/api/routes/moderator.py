"""
Moderator Routes
Dashboard, Users view, and System Settings
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from src.core.extensions import db
from src.core.models import User, UploadedExam, StudentSubmission, SystemSettings
from sqlalchemy.exc import IntegrityError


moderator_bp = Blueprint('moderator', __name__)


def _require_moderator() -> bool:
    return current_user.is_authenticated and current_user.role == 'moderator'


@moderator_bp.route('/moderator/dashboard')
@login_required
def dashboard():
    if not _require_moderator():
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    total_users = User.query.count()
    total_exams = UploadedExam.query.count()
    total_submissions = StudentSubmission.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).all()

    return render_template(
        'moderator/dashboard.html',
        total_users=total_users,
        total_exams=total_exams,
        total_submissions=total_submissions,
        recent_users=recent_users,
    )


@moderator_bp.route('/moderator/users', endpoint='moderator_users')
@login_required
def users():
    if not _require_moderator():
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    all_users = User.query.order_by(User.created_at.desc()).all()
    # Pass current time value to avoid callable issues in Jinja
    return render_template('moderator/users.html', users=all_users, now_utc=datetime.utcnow())


@moderator_bp.route('/moderator/system', endpoint='moderator_system')
@login_required
def system():
    if not _require_moderator():
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    settings_rows = SystemSettings.query.all()
    settings = {row.setting_key: row.setting_value for row in settings_rows}
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

    return render_template(
        'moderator/system.html',
        settings=settings,
        last_updated=now,
    )


@moderator_bp.route('/moderator/system/save_settings', methods=['POST'])
@login_required
def save_settings():
    if not _require_moderator():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    data = request.get_json(silent=True) or {}
    settings = data.get('settings', {})
    try:
        for key, value in settings.items():
            key = str(key)
            value = str(value) if not isinstance(value, str) else value
            existing = SystemSettings.query.filter_by(setting_key=key).first()
            if existing:
                existing.setting_value = value
                existing.updated_at = datetime.utcnow()
                existing.updated_by = current_user.id
            else:
                db.session.add(SystemSettings(
                    setting_key=key,
                    setting_value=value,
                    setting_type='string',
                    updated_by=current_user.id
                ))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@moderator_bp.route('/moderator/system/confirm_settings', methods=['POST'])
@login_required
def confirm_settings():
    if not _require_moderator():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    # In this simplified app, confirmation is a no-op
    return jsonify({'success': True})


# ---- User management endpoints ----

@moderator_bp.route('/moderator/user/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_user(user_id: int):
    if not _require_moderator():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    try:
        user = User.query.get_or_404(user_id)
        form = request.form
        username = form.get('username', user.username).strip()
        email = form.get('email', user.email).strip()
        language = form.get('language', user.language or '').strip()
        role = form.get('role', user.role).strip()

        # Basic uniqueness checks
        if username != user.username and User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        if email != user.email and User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'Email already exists'}), 400

        user.username = username or user.username
        user.email = email or user.email
        user.language = language or user.language
        if role in ['student', 'instructor', 'moderator']:
            user.role = role

        db.session.commit()
        return jsonify({'success': True})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Constraint error'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@moderator_bp.route('/moderator/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id: int):
    if not _require_moderator():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    try:
        if user_id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@moderator_bp.route('/moderator/user/<int:user_id>/suspend', methods=['POST'])
@login_required
def suspend_user(user_id: int):
    if not _require_moderator():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    try:
        user = User.query.get_or_404(user_id)
        days_raw = request.form.get('days', '0')
        try:
            days = int(days_raw)
        except ValueError:
            days = 0
        if days > 0:
            user.suspended_until = datetime.utcnow() + timedelta(days=days)
            user.is_active = False
        else:
            user.suspended_until = None
            user.is_active = False
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@moderator_bp.route('/moderator/user/<int:user_id>/unsuspend', methods=['POST'])
@login_required
def unsuspend_user(user_id: int):
    if not _require_moderator():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    try:
        user = User.query.get_or_404(user_id)
        user.suspended_until = None
        user.is_active = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


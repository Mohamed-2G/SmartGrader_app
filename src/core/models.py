"""
models.py - SQLAlchemy models for SmartGrader
"""
from flask_login import UserMixin
from datetime import datetime
from src.core.extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='instructor')  # instructor, moderator, student
    language = db.Column(db.String(20), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    suspended_until = db.Column(db.DateTime, nullable=True)
    profile_picture = db.Column(db.String(200))
    bio = db.Column(db.Text)
    
    # Password reset fields
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    reset_code = db.Column(db.String(6), nullable=True)  # 6-digit verification code
    reset_code_expires = db.Column(db.DateTime, nullable=True)
    moderator_reset_requested = db.Column(db.Boolean, default=False)
    moderator_reset_requested_at = db.Column(db.DateTime, nullable=True)
    
    # Security question fields
    security_question = db.Column(db.String(200), nullable=True)
    security_answer = db.Column(db.String(200), nullable=True)
    
    # Relationships
    exams = db.relationship('Exam', backref='creator', lazy=True)
    uploaded_exams = db.relationship('UploadedExam', backref='instructor', lazy=True)
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    messages_received = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True)

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    setting_type = db.Column(db.String(20), default='string')  # string, integer, float, boolean
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject = db.Column(db.String(100))
    total_points = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    # Relationships
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='exam', lazy=True, cascade='all, delete-orphan')

class UploadedExam(db.Model):
    """New model for uploaded exam files"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject = db.Column(db.String(100))
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(500), nullable=False)  # Path to uploaded exam file
    file_type = db.Column(db.String(20), nullable=False)  # pdf, image, document
    original_filename = db.Column(db.String(200), nullable=False)
    is_processed = db.Column(db.Boolean, default=False)  # Whether AI has processed the exam
    processing_status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    processing_result = db.Column(db.Text)  # JSON string with extracted questions and answers
    total_questions = db.Column(db.Integer, default=0)
    total_points = db.Column(db.Integer, default=0)
    # Relationships
    student_submissions = db.relationship('StudentSubmission', backref='uploaded_exam', lazy=True, cascade='all, delete-orphan')

class StudentSubmission(db.Model):
    """New model for student submissions to uploaded exams"""
    id = db.Column(db.Integer, primary_key=True)
    uploaded_exam_id = db.Column(db.Integer, db.ForeignKey('uploaded_exam.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50), nullable=False)  # Student number/tag
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    submission_file_path = db.Column(db.String(500), nullable=False)  # Path to student's answer file
    file_type = db.Column(db.String(20), nullable=False)  # pdf, image, document
    original_filename = db.Column(db.String(200), nullable=False)
    is_graded = db.Column(db.Boolean, default=False)
    total_score = db.Column(db.Float, default=0)
    max_score = db.Column(db.Float, default=0)
    grading_status = db.Column(db.String(50), default='pending')  # pending, grading, completed, failed
    grading_result = db.Column(db.Text)  # JSON string with detailed grading results
    # Relationships
    question_answers = db.relationship('QuestionAnswer', backref='student_submission', lazy=True, cascade='all, delete-orphan')

class QuestionAnswer(db.Model):
    """New model for individual question answers in student submissions"""
    id = db.Column(db.Integer, primary_key=True)
    student_submission_id = db.Column(db.Integer, db.ForeignKey('student_submission.id'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)  # Which question this answer is for
    question_text = db.Column(db.Text)  # Extracted question text
    answer_text = db.Column(db.Text)  # Extracted answer text
    answer_image_path = db.Column(db.String(500))  # If answer is in image format
    score = db.Column(db.Float, default=0)
    max_score = db.Column(db.Float, default=0)
    feedback = db.Column(db.Text)
    graded_at = db.Column(db.DateTime)
    confidence_score = db.Column(db.Float)  # AI confidence in the grading

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    rubric = db.Column(db.Text, nullable=False)  # JSON string
    points = db.Column(db.Integer, default=0)
    question_number = db.Column(db.Integer)
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_score = db.Column(db.Float, default=0)
    max_score = db.Column(db.Float, default=0)
    is_graded = db.Column(db.Boolean, default=False)
    # Relationships
    answers = db.relationship('Answer', backref='submission', lazy=True, cascade='all, delete-orphan')

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    answer_file = db.Column(db.String(200))  # Path to uploaded file (PDF, image, etc.)
    file_type = db.Column(db.String(20))  # pdf, image, text
    score = db.Column(db.Float, default=0)
    max_score = db.Column(db.Float, default=0)
    feedback = db.Column(db.Text)
    graded_at = db.Column(db.DateTime)
    graded_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    message_type = db.Column(db.String(20), default='text')  # text, file, system
    # For file attachments
    attachment_path = db.Column(db.String(200))
    attachment_name = db.Column(db.String(200))

# FileUpload model removed - functionality disabled

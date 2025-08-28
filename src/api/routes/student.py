"""
Student Routes
Handles student-specific functionality for viewing available exams and submitting answers
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename

from src.core.models import UploadedExam, StudentSubmission, QuestionAnswer, db
from src.core.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

# Create Blueprint
student_bp = Blueprint('student', __name__)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_answers_from_submission(submission_text, questions):
    """
    Parse answers from a student's submission text and match them to questions.
    Works even when multiple answers are in the same line.
    """
    import re
    
    parsed_answers = {}
    
    # Join all lines into one string
    text = " ".join(line.strip() for line in submission_text.split("\n") if line.strip())

     # Note: added optional plural forms and case-insensitivity
    prefix_pattern = r'(?:Answer|Ans|Response|Reply|Question|Q|Reponse|Réponse|Répondre|Question|Soru|Cevap|Yanıt|سؤال|إجابة|جواب|رد)'
    
    # Split by "Answer X :" pattern, keeping the number
    parts = re.split(rf'(?:{prefix_pattern})\s+(\d+)\s*:\s*', text, flags=re.IGNORECASE)
    
    # parts looks like: ['', '1', 'Bonjour, ...', '2', 'Le matin ...', '3', 'Client...', '4', 'L’été dernier...']
    # Iterate in pairs (number, answer_text)
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        answer_text = parts[i + 1].strip()
        parsed_answers[num] = answer_text
    
    # Ensure all questions are present (fill missing with placeholder)
    for q in questions:
        if q['id'] not in parsed_answers:
            parsed_answers[q['id']] = "No specific answer found for this question in the uploaded file."
    
    return parsed_answers



def extract_keywords_from_question(question_text):
    """Extract key terms from a question to help identify relevant answers"""
    import re
    
    # Remove common question words and extract key terms
    question_lower = question_text.lower()
    
    # Remove common question words
    question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'describe', 'explain', 'discuss', 'analyze', 'compare', 'contrast', 'evaluate', 'define', 'list', 'outline']
    for word in question_words:
        question_lower = question_lower.replace(word, '')
    
    # Extract potential key terms (words that might appear in answers)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', question_lower)
    
    # Filter out common words
    common_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among']
    keywords = [word for word in words if word not in common_words]
    
    return keywords[:5]  # Return top 5 keywords

def extract_relevant_content(text, keywords):
    """Extract content that might be relevant to a question based on keywords"""
    lines = text.split('\n')
    relevant_lines = []
    
    for line in lines:
        line_lower = line.lower()
        # Check if line contains any of the keywords
        if any(keyword.lower() in line_lower for keyword in keywords):
            relevant_lines.append(line.strip())
    
    if relevant_lines:
        return '\n'.join(relevant_lines)
    
    return ""

@student_bp.route('/student/dashboard')
@login_required
def dashboard():
    """Student dashboard - shows available exams and submission history"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Get all available exams (processed exams)
        available_exams = UploadedExam.query.filter_by(is_processed=True).order_by(UploadedExam.uploaded_at.desc()).all()
        
        # Get student's submissions
        # Since student_id now contains the actual student ID number, we'll show all submissions for now
        # In production, you'd want to link submissions to user accounts properly
        student_submissions = StudentSubmission.query.order_by(StudentSubmission.submitted_at.desc()).all()
        
        # Statistics
        total_submissions = len(student_submissions)
        graded_submissions = len([s for s in student_submissions if s.is_graded])
        pending_submissions = total_submissions - graded_submissions
        average_score = 0
        if graded_submissions > 0:
            total_score = sum([s.total_score for s in student_submissions if s.is_graded])
            average_score = total_score / graded_submissions
        
    except Exception as e:
        # If database models don't exist yet, provide default values
        print(f"Database error: {e}")
        available_exams = []
        student_submissions = []
        total_submissions = 0
        graded_submissions = 0
        pending_submissions = 0
        average_score = 0
    
    return render_template('student/dashboard.html', 
                         available_exams=available_exams,
                         student_submissions=student_submissions,
                         total_submissions=total_submissions,
                         graded_submissions=graded_submissions,
                         pending_submissions=pending_submissions,
                         average_score=average_score)

@student_bp.route('/student/exams')
@login_required
def exams():
    """List all available exams"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        available_exams = UploadedExam.query.filter_by(is_processed=True).order_by(UploadedExam.uploaded_at.desc()).all()
    except Exception as e:
        print(f"Database error: {e}")
        available_exams = []
    
    return render_template('student/exams.html', exams=available_exams)

@student_bp.route('/student/exam/<int:exam_id>')
@login_required
def view_exam(exam_id):
    """View details of an available exam"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = UploadedExam.query.get_or_404(exam_id)
        
        # Check if exam is processed
        if not exam.is_processed:
            flash('This exam is not available yet.', 'error')
            return redirect(url_for('student.exams'))
        
        # Check if student already submitted this exam
        # Since student_id now contains the actual student ID number, we'll use a different approach
        # For now, we'll allow multiple submissions - in production you'd want proper linking
        existing_submission = None
        
    except Exception as e:
        print(f"Database error: {e}")
        flash('Exam not found.', 'error')
        return redirect(url_for('student.exams'))
    
    return render_template('student/view_exam.html', 
                         exam=exam, 
                         existing_submission=existing_submission)

@student_bp.route('/student/exam/<int:exam_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_exam(exam_id):
    """Submit answers for an exam"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = UploadedExam.query.get_or_404(exam_id)
        
        # Check if exam is processed
        if not exam.is_processed:
            flash('This exam is not available yet.', 'error')
            return redirect(url_for('student.exams'))
        
    except Exception as e:
        print(f"Database error: {e}")
        flash('Exam not found.', 'error')
        return redirect(url_for('student.exams'))
    
    if request.method == 'POST':
        try:
            # Parse the processing result to get questions
            questions = []
            if exam.processing_result:
                try:
                    import json
                    processing_data = json.loads(exam.processing_result)
                    questions_data = processing_data.get('questions', [])
                    
                    for i, q_data in enumerate(questions_data, 1):
                        question = {
                            'id': i,
                            'question_text': q_data.get('text', q_data.get('question', f'Question {i}')),
                            'points': q_data.get('max_points', q_data.get('points', 10)),
                            'answer': q_data.get('answer', '')
                        }
                        questions.append(question)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error parsing exam questions: {e}")
                    return jsonify({
                        'success': False,
                        'error': f'Failed to parse exam questions: {str(e)}'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': 'Exam has not been processed yet. Please contact your instructor.'
                }), 400
            
            # Calculate total points
            total_points = sum(q['points'] for q in questions)
            
            # Process answers and files first to determine the main submission file
            answers_data = []
            main_submission_file = None
            main_file_type = "text"
            main_filename = "text_answers.txt"
            
            # Check if there's a main submission file
            main_file_obj = request.files.get('main_submission_file')
            if main_file_obj and main_file_obj.filename:
                if allowed_file(main_file_obj.filename):
                    filename = secure_filename(main_file_obj.filename)
                    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_student_{current_user.id}_main_{filename}"
                    upload_dir = os.path.join(UPLOAD_FOLDER, 'student_submissions')
                    os.makedirs(upload_dir, exist_ok=True)
                    main_submission_file = os.path.join(upload_dir, unique_filename)
                    main_file_obj.save(main_submission_file)
                    main_file_type = filename.rsplit('.', 1)[1].lower()
                    main_filename = filename
            
            # Create student submission record
            submission = StudentSubmission(
                uploaded_exam_id=exam_id,
                student_name=current_user.username,
                student_id=str(current_user.id),
                submission_file_path=main_submission_file if main_submission_file else "",
                file_type=main_file_type,
                original_filename=main_filename,
                max_score=total_points
            )
            
            db.session.add(submission)
            db.session.flush()  # Get the submission ID
            
            # Process individual question answers and files
            for question in questions:
                question_id = question['id']
                answer_text = request.form.get(f'answer_{question_id}', '').strip()
                file_obj = request.files.get(f'file_{question_id}')
                
                # Handle file upload if present
                file_path = ""
                if file_obj and file_obj.filename:
                    if allowed_file(file_obj.filename):
                        filename = secure_filename(file_obj.filename)
                        unique_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_student_{current_user.id}_q{question_id}_{filename}"
                        upload_dir = os.path.join(UPLOAD_FOLDER, 'student_submissions')
                        os.makedirs(upload_dir, exist_ok=True)
                        file_path = os.path.join(upload_dir, unique_filename)
                        file_obj.save(file_path)
                
                # Create question answer record
                question_answer = QuestionAnswer(
                    student_submission_id=submission.id,
                    question_number=question_id,
                    question_text=question['question_text'],
                    answer_text=answer_text,
                    answer_image_path=file_path if file_path else None,
                    max_score=question['points'],
                    score=0
                )
                db.session.add(question_answer)
                answers_data.append({
                    'question_number': question_id,
                    'question_text': question['question_text'],
                    'answer': answer_text,
                    'file_path': file_path
                })
            
            # If main submission file was uploaded, extract answers from it
            if main_submission_file:
                try:
                    # Extract text from the uploaded file
                    from src.utils.helpers import extract_text_from_file
                    submission_text = extract_text_from_file(main_submission_file, main_file_type)
                    # print("submission text", submission_text)
                    
                    # Parse answers from the submission text and match to questions
                    parsed_answers = parse_answers_from_submission(submission_text, questions)
                    # print(parsed_answers)
                    
                    # Update the question answers with parsed answers
                    for question_answer in db.session.query(QuestionAnswer).filter_by(student_submission_id=submission.id).all():
                        question_number = question_answer.question_number
                        if question_number in parsed_answers:
                            question_answer.answer_text = parsed_answers[question_number]
                    
                    print(f"✅ Successfully parsed {len(parsed_answers)} answers from uploaded file")
                    
                    # Add a success message to the response
                    success_message = f"Exam submitted successfully! {len(parsed_answers)} answers were automatically detected from your uploaded file."
                    
                except Exception as e:
                    print(f"⚠️ Error parsing answers from uploaded file: {e}")
                    # Continue with manual answers if parsing fails
                    success_message = "Exam submitted successfully! (Note: Could not parse answers from uploaded file, using manual answers instead)"
            
            # If no main submission file, create a text file with all answers
            if not main_submission_file:
                import tempfile
                answer_text = "\n\n".join([f"Question {qa['question_number']}:\n{qa['answer']}" for qa in answers_data])
                temp_file_path = os.path.join(UPLOAD_FOLDER, 'student_submissions', f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_student_{current_user.id}_answers.txt")
                os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(answer_text)
                submission.submission_file_path = temp_file_path
            
            db.session.commit()
            
            # Return JSON response for AJAX
            return jsonify({
                'success': True,
                'submission_id': submission.id,
                'message': success_message if 'success_message' in locals() else 'Exam submitted successfully!'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error submitting exam: {e}")
            return jsonify({
                'success': False,
                'error': f'Error submitting exam: {str(e)}'
            })
    
    # GET request - redirect to take exam
    return redirect(url_for('student.take_exam', exam_id=exam_id))

@student_bp.route('/student/submission/<int:submission_id>')
@login_required
def view_submission(submission_id):
    """View a specific submission and its results"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        submission = StudentSubmission.query.get_or_404(submission_id)
        
        # Check if this submission belongs to the current student
        # Since student_id now contains the actual student ID number, we'll use a different approach
        # For now, we'll allow students to view submissions - in production you'd want proper authentication
        pass
        
        # Get question answers if graded
        question_answers = []
        if submission.is_graded:
            question_answers = QuestionAnswer.query.filter_by(
                student_submission_id=submission_id
            ).order_by(QuestionAnswer.question_number).all()
        
    except Exception as e:
        print(f"Database error: {e}")
        flash('Submission not found.', 'error')
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/view_submission.html', 
                         submission=submission,
                         question_answers=question_answers)

@student_bp.route('/student/submission/<int:submission_id>/download')
@login_required
def download_submission(submission_id):
    """Download the submitted answer file"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        submission = StudentSubmission.query.get_or_404(submission_id)
        
        # Check if this submission belongs to the current student
        # Since student_id now contains the actual student ID number, we'll use a different approach
        # For now, we'll allow students to view submissions - in production you'd want proper authentication
        pass
        
        if os.path.exists(submission.submission_file_path):
            return send_file(submission.submission_file_path, 
                           as_attachment=True, 
                           download_name=submission.original_filename)
        else:
            flash('File not found.', 'error')
            return redirect(url_for('student.view_submission', submission_id=submission_id))
            
    except Exception as e:
        print(f"Database error: {e}")
        flash('Submission not found.', 'error')
        return redirect(url_for('student.dashboard'))

@student_bp.route('/student/results')
@login_required
def results():
    """View all graded results"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        # For now, show all graded submissions since we don't have proper student-submission linking
        # In production, you'd want to link submissions to user accounts properly
        graded_submissions = StudentSubmission.query.filter_by(
            is_graded=True
        ).order_by(StudentSubmission.submitted_at.desc()).all()
        
    except Exception as e:
        print(f"Database error: {e}")
        graded_submissions = []
    
    return render_template('student/results.html', submissions=graded_submissions)

@student_bp.route('/student/submissions')
@login_required
def submissions():
    """View all submissions (graded and ungraded)"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        # For now, show all submissions since we don't have proper student-submission linking
        # In production, you'd want to link submissions to user accounts properly
        all_submissions = StudentSubmission.query.order_by(StudentSubmission.submitted_at.desc()).all()
        
    except Exception as e:
        print(f"Database error: {e}")
        all_submissions = []
    
    return render_template('student/submissions.html', submissions=all_submissions)

@student_bp.route('/student/exam/<int:exam_id>/take')
@login_required
def take_exam(exam_id):
    """Take an exam - show questions and allow student to answer"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = UploadedExam.query.get_or_404(exam_id)
        
        # Check if exam is processed
        if not exam.is_processed:
            flash('This exam is not available yet.', 'error')
            return redirect(url_for('student.exams'))
        
        # Parse the processing result to get questions
        questions = []
        if exam.processing_result:
            try:
                import json
                processing_data = json.loads(exam.processing_result)
                questions_data = processing_data.get('questions', [])
                
                for i, q_data in enumerate(questions_data, 1):
                    question = {
                        'id': i,
                        'question_text': q_data.get('text', q_data.get('question', f'Question {i}')),
                        'points': q_data.get('max_points', q_data.get('points', 10)),
                        'answer': q_data.get('answer', '')
                    }
                    questions.append(question)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing exam questions: {e}")
                flash('Error loading exam questions. Please contact your instructor.', 'error')
                return redirect(url_for('student.exams'))
        else:
            flash('This exam has not been processed yet. Please contact your instructor.', 'error')
            return redirect(url_for('student.exams'))
        
        # Calculate total points
        total_points = sum(q['points'] for q in questions)
        
        # Add questions and total_points to exam object for template
        exam.questions = questions
        exam.total_points = total_points
        
    except Exception as e:
        print(f"Database error: {e}")
        flash('Exam not found.', 'error')
        return redirect(url_for('student.exams'))
    
    return render_template('student/take_exam.html', exam=exam)

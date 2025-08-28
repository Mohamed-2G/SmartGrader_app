"""
Instructor Routes
Handles instructor-specific functionality for uploading exams and managing student submissions
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename

from src.core.models import UploadedExam, StudentSubmission, QuestionAnswer, db
from src.core.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from src.api.routes.ai_grading import grade_with_deepseek, grade_with_fallback
from src.services.grader.exam_grader import ExamGrader

from src.core.config import DEEPSEEK_API_KEY
from src.utils.helpers import extract_text_from_pdf, extract_text_from_image, allowed_file

# Create Blueprint
instructor_bp = Blueprint('instructor', __name__)

def extract_text_from_file(file_path, file_type):
    """Extract text content from different file types using improved helpers"""
    try:
        if file_type == 'pdf':
            # Use improved PDF extraction from helpers
            return extract_text_from_pdf(file_path)
        
        elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
            # Use improved image OCR from helpers
            return extract_text_from_image(file_path)
        
        elif file_type in ['txt', 'doc', 'docx', 'document', 'text']:
            # For text files, read directly
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read().strip()
        
        elif file_type == 'image':
            # Handle generic 'image' type
            return extract_text_from_image(file_path)
        
        else:
            return f"Unsupported file type: {file_type}. Supported types: PDF, images (JPG, PNG, GIF, BMP, TIFF), and text files (TXT, DOC, DOCX)"
            
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return f"Error extracting text: {str(e)}"

def extract_answer_for_question(submission_text, question_number, question_text):
    """Extract the specific answer for a given question from the submission text"""
    try:
        # Split the submission text into lines
        lines = submission_text.split('\n')
        
        # Enhanced patterns for better answer detection
        answer_start_patterns = [
            f"Question {question_number}:",
            f"Q{question_number}:",
            f"{question_number}.",
            f"{question_number})",
            f"Answer {question_number}:",
            f"Question {question_number}",
            f"Q{question_number}",
            f"Q{question_number}.",
            f"Q{question_number})",
            f"Answer to Question {question_number}:",
            f"Answer to Q{question_number}:",
            f"Q{question_number}.",
            f"Q{question_number})",
            f"Answer {question_number}.",
            f"Answer {question_number})",
            f"Part {question_number}:",
            f"Section {question_number}:",
            f"{question_number}.",
            f"{question_number})",
            f"{question_number}.",
            f"{question_number})",
        ]
        
        # Also look for patterns that indicate the end of an answer
        answer_end_patterns = [
            f"Question {question_number + 1}:",
            f"Q{question_number + 1}:",
            f"{question_number + 1}.",
            f"{question_number + 1})",
            f"Answer {question_number + 1}:",
            f"Part {question_number + 1}:",
            f"Section {question_number + 1}:",
        ]
        
        answer_lines = []
        found_answer = False
        current_answer_start = -1
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            line_original = line.strip()
            
            # Check if this line starts a new question answer
            for pattern in answer_start_patterns:
                if line_lower.startswith(pattern.lower()):
                    # If we find the next question, stop here
                    if found_answer:
                        break
                    found_answer = True
                    current_answer_start = i
                    # Include the question header line in the answer
                    if line_original:
                        answer_lines.append(line_original)
                    continue
            
            # If we found the answer start, collect lines until we hit another question
            if found_answer:
                # Check if this line starts another question
                is_next_question = False
                for pattern in answer_end_patterns:
                    if line_lower.startswith(pattern.lower()):
                        is_next_question = True
                        break
                
                if is_next_question:
                    break
                
                # Add this line to the answer
                if line_original:
                    answer_lines.append(line_original)
        
        # If we found specific answer lines, return them
        if answer_lines:
            answer_text = '\n'.join(answer_lines)
            print(f"✅ Found specific answer for Question {question_number}: {len(answer_text)} characters")
            return answer_text
        
        # If no specific answer found, try AI-based extraction
        print(f"⚠️ No specific answer markers found for Question {question_number}, trying AI-based extraction...")
        
        try:
            # Use AI to extract the specific answer for this question
            import requests
            import json
            
            api_url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            TASK: Extract the specific answer for Question {question_number} from the student's submission.

            QUESTION {question_number}: {question_text}

            STUDENT'S FULL SUBMISSION:
            {submission_text}

            INSTRUCTIONS:
            - Find the specific answer that corresponds to Question {question_number}
            - Look for any text that directly answers this question
            - If the student has organized their answers with numbers, letters, or sections, use those markers
            - If no clear markers exist, find the most relevant content that answers this specific question
            - Return ONLY the answer text, not the question or any other content
            - If you cannot find a specific answer, return "No specific answer found for this question"

            REQUIRED OUTPUT FORMAT (JSON):
            {{
                "answer": "the specific answer text for question {question_number}"
            }}
            """
            
            payload = {
                "model": "deepseek-chat",  # Use chat model for simple extraction tasks
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing student submissions and extracting specific answers to questions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
                # Try to parse JSON response
                try:
                    json_response = json.loads(ai_response.strip())
                    ai_answer = json_response.get('answer', '')
                    if ai_answer and ai_answer != "No specific answer found for this question":
                        print(f"✅ AI extracted answer for Question {question_number}: {len(ai_answer)} characters")
                        return ai_answer
                except json.JSONDecodeError:
                    # If JSON parsing fails, use the raw response
                    if ai_response and "No specific answer found" not in ai_response:
                        print(f"✅ AI extracted answer for Question {question_number}: {len(ai_response)} characters")
                        return ai_response
                        
        except Exception as ai_error:
            print(f"⚠️ AI extraction failed for Question {question_number}: {ai_error}")
        
        # Final fallback: return a portion of the submission text
        print(f"⚠️ No specific answer found for Question {question_number}, using fallback...")
        
        # Try to find a reasonable section of the submission text
        total_lines = len(lines)
        if total_lines > 0:
            # For the first question, take the first third
            if question_number == 1:
                section_lines = lines[:total_lines//3]
            # For the last question, take the last third
            elif question_number >= 3:  # Assuming at least 3 questions
                section_lines = lines[2*total_lines//3:]
            # For middle questions, take the middle section
            else:
                start = (question_number - 1) * total_lines // 3
                end = question_number * total_lines // 3
                section_lines = lines[start:end]
            
            fallback_text = '\n'.join([line.strip() for line in section_lines if line.strip()])
            if fallback_text:
                print(f"✅ Using fallback section for Question {question_number}: {len(fallback_text)} characters")
                return fallback_text
        
        # If all else fails, return a limited portion of the full text
        if len(submission_text) > 500:
            return submission_text[:500] + "..."
        return submission_text
        
    except Exception as e:
        print(f"Error extracting answer for question {question_number}: {e}")
        return submission_text

def extract_questions_with_ai(exam_text, grader):
    """Use AI to extract questions from exam text with improved prompt"""
    try:
        # Create a more detailed prompt for better question extraction
        prompt = f"""
        TASK: Extract all questions from the provided exam text and return them in JSON format.

        EXAM TEXT TO ANALYZE:
        {exam_text}

        INSTRUCTIONS:
        - Look for ANY numbered questions: 1., 2., 3., 4., 5., etc.
        - Look for "Question X:" format (with or without subtitles)
        - Look for "Q1:", "Q2:", "Q3:" format
        - Look for lettered questions: a., b., c., d., etc.
        - Look for Roman numerals: i., ii., iii., iv., etc.
        - Look for "Part A", "Part B", "Part C" format
        - Look for questions that start with action verbs: Describe, Explain, Discuss, Analyze, Compare, Evaluate, Define, etc.
        - Include the COMPLETE question text including any subtitles or context
        - If points are specified like "(5 points)", "(10 marks)", use those exact values
        - If no points specified, estimate based on question complexity:
            - Simple questions (1-2 sentences): 5 points
            - Medium questions (3-5 sentences): 10 points
            - Complex questions (long explanations): 15-20 points
            - Essay questions: 20-25 points

        EXAMPLES OF WHAT TO LOOK FOR:
        - "1. Describe the process of..."
        - "Question 2: Explain how..."
        - "Q3: Compare and contrast..."
        - "a) Define the term..."
        - "Part A: Analyze the following..."
        - "i. Discuss the implications..."
        - "Describe the significance of..."

        REQUIRED OUTPUT FORMAT (JSON):
        {{
            "questions": [
                {{
                    "number": 1,
                    "text": "complete question text here including any subtitles",
                    "max_points": 10
                }}
            ]
        }}

        IMPORTANT: This is a question extraction task, NOT a grading task. Do NOT grade anything. Only extract and list the questions found in the exam text.
        """
        
        print(f"🔍 Extracting questions from exam text (length: {len(exam_text)} characters)")
        print(f"📄 First 500 characters: {exam_text[:500]}...")
        
        # Use direct API call instead of grading interface
        try:
            import requests
            import json
            
            # Direct API call to DeepSeek for question extraction
            api_url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {grader.deepseek_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",  # Use chat model for simple extraction tasks
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing exam content and extracting questions. Your task is to identify and extract all questions from exam text, not to grade anything."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.1,
                "top_p": 0.9
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                print(f"🤖 AI Response (first 500 chars): {ai_response[:500]}...")
                
                # Try to parse as JSON
                try:
                    # Look for JSON in the response
                    import re
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        print(f"📋 Found JSON: {json_str}")
                        parsed_data = json.loads(json_str)
                        questions = parsed_data.get('questions', [])
                        
                        # Validate and format questions
                        formatted_questions = []
                        for q in questions:
                            if isinstance(q, dict) and 'text' in q:
                                formatted_questions.append({
                                    'number': q.get('number', 1),
                                    'text': q.get('text', ''),
                                    'max_points': q.get('max_points', 10)
                                })
                        
                        if formatted_questions:
                            print(f"✅ Successfully extracted {len(formatted_questions)} questions via JSON")
                            return formatted_questions
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"❌ Failed to parse JSON response: {e}")
            else:
                print(f"❌ API request failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Direct API call failed: {e}")
        
        # Fallback to direct text parsing if AI fails
        print("🔄 Falling back to direct text parsing...")
        return extract_questions_directly(exam_text)
        
    except Exception as e:
        print(f"❌ Error in question extraction: {e}")
        return extract_questions_directly(exam_text)

def extract_questions_directly(exam_text):
    """Extract questions directly from exam text without AI - format agnostic"""
    try:
        import re
        
        print("🔍 Direct text parsing mode (format agnostic)...")
        questions = []
        lines = exam_text.split('\n')
        current_question = None
        question_counter = 1
        
        # Define flexible question patterns
        question_patterns = [
            r'^Question\s+(\d+):\s*(.*)',  # Question 1: ...
            r'^(\d+)\.\s*(.*)',  # 1. ...
            r'^Q\.?\s*(\d+):?\s*(.*)',  # Q1: ...
            r'^(\d+)\)\s*(.*)',  # 1) ...
            r'^([a-z])\.\s*(.*)',  # a. ...
            r'^([A-Z])\.\s*(.*)',  # A. ...
            r'^([ivxlcdm]+)\.\s*(.*)',  # i. ii. iii. ...
            r'^Part\s+([A-Z]):\s*(.*)',  # Part A: ...
        ]
        
        # Action verbs that often indicate questions
        action_verbs = [
            'describe', 'explain', 'discuss', 'analyze', 'compare', 'contrast', 
            'evaluate', 'assess', 'examine', 'identify', 'define', 'list',
            'outline', 'summarize', 'interpret', 'calculate', 'solve', 'prove',
            'demonstrate', 'illustrate', 'examine', 'investigate', 'explore'
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new question using various patterns
            is_new_question = False
            q_num = None
            q_text = ""
            
            # Try all question patterns
            for pattern in question_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    is_new_question = True
                    if pattern == r'^Question\s+(\d+):\s*(.*)':
                        q_num = int(match.group(1))
                        q_text = match.group(2).strip()
                        # For "Question X: Subtitle" format, don't treat subtitle as separate question
                        if q_text and not any(verb in q_text.lower() for verb in action_verbs):
                            # This is likely a subtitle, not a question
                            is_new_question = False
                            break
                    elif pattern == r'^(\d+)\.\s*(.*)':
                        q_num = int(match.group(1))
                        q_text = match.group(2).strip()
                    elif pattern == r'^Q\.?\s*(\d+):?\s*(.*)':
                        q_num = int(match.group(1))
                        q_text = match.group(2).strip()
                    elif pattern == r'^(\d+)\)\s*(.*)':
                        q_num = int(match.group(1))
                        q_text = match.group(2).strip()
                    elif pattern == r'^([a-z])\.\s*(.*)':
                        q_num = ord(match.group(1).lower()) - ord('a') + 1
                        q_text = match.group(2).strip()
                    elif pattern == r'^([A-Z])\.\s*(.*)':
                        q_num = ord(match.group(1).upper()) - ord('A') + 1
                        q_text = match.group(2).strip()
                    elif pattern == r'^([ivxlcdm]+)\.\s*(.*)':
                        # Convert roman numeral to number
                        roman = match.group(1).lower()
                        roman_dict = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
                        q_num = sum(roman_dict.get(c, 0) for c in roman)
                        q_text = match.group(2).strip()
                    elif pattern == r'^Part\s+([A-Z]):\s*(.*)':
                        q_num = ord(match.group(1).upper()) - ord('A') + 1
                        q_text = match.group(2).strip()
                    break
            
            # If no pattern matched, check if line starts with action verb (might be a question)
            if not is_new_question:
                line_lower = line.lower()
                if any(verb in line_lower for verb in action_verbs) and len(line) > 20:
                    # This might be a question without explicit numbering
                    is_new_question = True
                    q_num = question_counter
                    q_text = line
            
            if is_new_question:
                # Save previous question if exists
                if current_question:
                    questions.append(current_question)
                
                # Extract points if specified
                points_match = re.search(r'\((\d+)\s*points?\)$', q_text, re.IGNORECASE)
                if points_match:
                    points = int(points_match.group(1))
                    q_text = re.sub(r'\(\d+\s*points?\)$', '', q_text, flags=re.IGNORECASE).strip()
                else:
                    # Estimate points based on text length and complexity
                    text_length = len(q_text)
                    if text_length < 50:
                        points = 5
                    elif text_length < 150:
                        points = 10
                    else:
                        points = 15
                
                current_question = {
                    'number': q_num,
                    'text': q_text,
                    'max_points': points
                }
                question_counter = max(question_counter, q_num + 1)
                continue
            
            # If we have a current question, append this line to it
            elif current_question and line:
                # Check if this line starts a new question (to avoid merging questions)
                is_next_question = False
                for pattern in question_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        is_next_question = True
                        break
                
                if is_next_question or any(verb in line.lower() for verb in action_verbs):
                    # This is a new question, save the current one and start a new one
                    questions.append(current_question)
                    current_question = None
                    continue
                else:
                    # This might be continuation of the current question
                    current_question['text'] += ' ' + line
        
        # Add the last question if exists
        if current_question:
            questions.append(current_question)
        
        print(f"📝 Direct parsing extracted {len(questions)} questions")
        
        # If still no questions found, create a basic fallback
        if not questions:
            print("⚠️ No questions found in direct parsing, creating basic fallback...")
            questions = [
                {
                    'number': 1,
                    'text': 'Question extracted from exam content',
                    'max_points': 10
                }
            ]
        
        return questions
        
    except Exception as e:
        print(f"❌ Error in direct text parsing: {e}")
        return [
            {
                'number': 1,
                'text': 'Question extracted from exam content',
                'max_points': 10
            }
        ]

@instructor_bp.route('/instructor/dashboard')
@login_required
def dashboard():
    """Instructor dashboard - shows uploaded exams and recent submissions"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Get instructor's uploaded exams
        uploaded_exams = UploadedExam.query.filter_by(instructor_id=current_user.id).order_by(UploadedExam.uploaded_at.desc()).all()
        
        # Get recent submissions
        recent_submissions = StudentSubmission.query.join(UploadedExam).filter(
            UploadedExam.instructor_id == current_user.id
        ).order_by(StudentSubmission.submitted_at.desc()).limit(10).all()
        
        # Statistics
        total_exams = len(uploaded_exams)
        total_submissions = StudentSubmission.query.join(UploadedExam).filter(
            UploadedExam.instructor_id == current_user.id
        ).count()
        pending_grading = StudentSubmission.query.join(UploadedExam).filter(
            UploadedExam.instructor_id == current_user.id,
            StudentSubmission.is_graded == False
        ).count()
        
    except Exception as e:
        # If database models don't exist yet, provide default values
        print(f"Database error: {e}")
        uploaded_exams = []
        recent_submissions = []
        total_exams = 0
        total_submissions = 0
        pending_grading = 0
    
    return render_template('instructor/dashboard.html', 
                         uploaded_exams=uploaded_exams,
                         recent_submissions=recent_submissions,
                         total_exams=total_exams,
                         total_submissions=total_submissions,
                         pending_grading=pending_grading,
                         )

@instructor_bp.route('/instructor/upload_exam', methods=['GET', 'POST'])
@login_required
def upload_exam():
    """Upload a new exam file or create manually"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        print("posting an exam")
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        subject = request.form.get('subject', '').strip()
        creation_method = request.form.get('creation_method', 'manual')
        
        if not title:
            flash('Exam title is required.', 'error')
            return render_template('instructor/upload_exam.html')
        
        try:
            # Handle manual question creation
            if creation_method == 'manual':
                question_texts = request.form.getlist('question_text[]')
                question_points = request.form.getlist('question_points[]')
                question_types = request.form.getlist('question_type[]')
                
                if not question_texts or not any(text.strip() for text in question_texts):
                    flash('At least one question is required.', 'error')
                    return render_template('instructor/upload_exam.html')
                
                # Create the exam record without file
                uploaded_exam = UploadedExam(
                    title=title,
                    description=description,
                    subject=subject,
                    file_path="",  # No file for manual creation
                    file_type="manual",
                    original_filename="",
                    instructor_id=current_user.id,
                    uploaded_at=datetime.utcnow(),
                    processing_status='completed',
                    is_processed=True
                )
                print("this was uploaded", uploaded_exam)
                
                db.session.add(uploaded_exam)
                
                # Create questions from manual input
                questions_data = []
                total_points = 0
                
                for i, (text, points, q_type) in enumerate(zip(question_texts, question_points, question_types)):
                    if text.strip():  # Only add non-empty questions
                        points_val = int(points) if points.isdigit() else 5
                        total_points += points_val
                        
                        questions_data.append({
                            'number': i + 1,
                            'text': text.strip(),
                            'max_points': points_val,
                            'type': q_type
                        })
                
                # Create processing result
                processing_result = {
                    'questions': questions_data,
                    'total_questions': len(questions_data),
                    'total_points': total_points,
                    'method': 'manual_creation'
                }
                
                uploaded_exam.processing_result = json.dumps(processing_result)
                uploaded_exam.total_questions = len(questions_data)
                uploaded_exam.total_points = total_points
                
                db.session.commit()
                flash(f'Exam created successfully! {len(questions_data)} questions added with {total_points} total points.', 'success')
                return redirect(url_for('instructor.view_exam', exam_id=uploaded_exam.id))
            
            # Handle file upload
            else:
                # Check if file was uploaded
                if 'exam_file' not in request.files:
                    flash('No exam file selected.', 'error')
                    return render_template('instructor/upload_exam.html')
                
                file = request.files['exam_file']
                
                # Check if file was selected
                if file.filename == '':
                    flash('No exam file selected.', 'error')
                    return render_template('instructor/upload_exam.html')
                
                # Check if file is allowed
                if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
                    flash('File type not allowed. Please upload PDF, image, or document files.', 'error')
                    return render_template('instructor/upload_exam.html')
                
                # Secure the filename
                filename = secure_filename(file.filename)
                
                # Create unique filename
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"exam_{timestamp}_{filename}"
                
                # Create exam uploads directory
                exam_uploads_dir = os.path.join(UPLOAD_FOLDER, 'exams')
                os.makedirs(exam_uploads_dir, exist_ok=True)
                
                # Save file to upload folder
                file_path = os.path.join(exam_uploads_dir, unique_filename)
                file.save(file_path)
                
                # Determine file type
                file_extension = filename.rsplit('.', 1)[1].lower()
                if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
                    file_type = 'image'
                elif file_extension == 'pdf':
                    file_type = 'pdf'
                else:
                    file_type = 'document'
                
                # Create uploaded exam record
                uploaded_exam = UploadedExam(
                    title=title,
                    description=description,
                    subject=subject,
                    instructor_id=current_user.id,
                    file_path=file_path,
                    file_type=file_type,
                    original_filename=filename,
                    uploaded_at=datetime.utcnow()
                )
                print("uploaded exam", uploaded_exam)
                
                db.session.add(uploaded_exam)
                
                # Automatically process the exam to extract questions
                try:
                    # Extract text from the uploaded exam file
                    exam_text = extract_text_from_file(file_path, file_type)
                    
                    if not exam_text or exam_text.startswith("Error extracting text"):
                        # Commit the exam record even if processing fails
                        # db.session.commit()
                        flash('Exam uploaded successfully! However, text extraction failed. Please manually process the exam.', 'warning')
                        return redirect(url_for('instructor.dashboard'))
                    
                    # Initialize the DeepSeek AI grader for question extraction
                    grader = ExamGrader(DEEPSEEK_API_KEY)
                    
                    # Use AI to extract questions from the exam content
                    questions = extract_questions_with_ai(exam_text, grader)
                    
                    # Calculate total points
                    total_points = sum(q.get('max_points', 10) for q in questions)
                    
                    # Create processing result
                    processing_result = {
                        'questions': questions,
                        'total_questions': len(questions),
                        'total_points': total_points,
                        'extracted_text': exam_text[:500] + "..." if len(exam_text) > 500 else exam_text  # Truncate for storage
                    }
                    
                    uploaded_exam.processing_status = 'completed'
                    uploaded_exam.is_processed = True
                    uploaded_exam.processing_result = json.dumps(processing_result)
                    uploaded_exam.total_questions = processing_result['total_questions']
                    uploaded_exam.total_points = processing_result['total_points']
                    
                    db.session.commit()
                    
                    flash(f'Exam uploaded and processed successfully! Extracted {len(questions)} questions from the exam content.', 'success')
                    
                except Exception as e:
                    print(f"Error auto-processing exam: {e}")
                    uploaded_exam.processing_status = 'failed'
                    # db.session.commit()
                    db.session.rollback()
                    flash('Exam uploaded successfully! However, automatic processing failed. Please manually process the exam.', 'warning')
                
                return redirect(url_for('instructor.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading exam: {str(e)}', 'error')
    
    return render_template('instructor/upload_exam.html')

@instructor_bp.route('/instructor/exams')
@login_required
def exams():
    """List all instructor's uploaded exams"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    uploaded_exams = UploadedExam.query.filter_by(instructor_id=current_user.id).order_by(UploadedExam.uploaded_at.desc()).all()
    return render_template('instructor/exams.html', uploaded_exams=uploaded_exams)

@instructor_bp.route('/instructor/exam/<int:exam_id>/add-questions')
@login_required
def add_questions_page(exam_id):
    """Show the manual question addition page"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = UploadedExam.query.get_or_404(exam_id)
        
        # Check if this exam belongs to the current instructor
        if exam.instructor_id != current_user.id:
            flash('Access denied. You can only modify your own exams.', 'error')
            return redirect(url_for('instructor.dashboard'))
        
        return render_template('instructor/add_questions.html', exam=exam)
        
    except Exception as e:
        print(f"Database error: {e}")
        flash('Exam not found.', 'error')
        return redirect(url_for('instructor.dashboard'))

@instructor_bp.route('/instructor/exam/<int:exam_id>/add-questions', methods=['POST'])
@login_required
def add_questions(exam_id):
    """Add questions manually to an exam"""
    if current_user.role != 'instructor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        exam = UploadedExam.query.get_or_404(exam_id)
        
        # Check if this exam belongs to the current instructor
        if exam.instructor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Get questions from JSON request
        data = request.get_json()
        questions_data = data.get('questions', [])
        
        if not questions_data:
            return jsonify({'success': False, 'error': 'No questions provided'}), 400
        
        # Create the processing result with the manually added questions
        processing_result = {
            'questions': questions_data,
            'total_questions': len(questions_data),
            'total_points': sum(q.get('max_points', 10) for q in questions_data),
            'method': 'manual_input'
        }
        
        # Update the exam
        exam.processing_result = json.dumps(processing_result)
        exam.is_processed = True
        exam.processing_status = 'completed'
        exam.total_questions = len(questions_data)
        exam.total_points = sum(q.get('max_points', 10) for q in questions_data)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully added {len(questions_data)} questions',
            'total_questions': len(questions_data),
            'total_points': sum(q.get('max_points', 10) for q in questions_data)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding questions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@instructor_bp.route('/instructor/exam/<int:exam_id>/delete', methods=['POST'])
@login_required
def delete_exam(exam_id):
    """Delete an uploaded exam"""
    if current_user.role != 'instructor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        exam = UploadedExam.query.get_or_404(exam_id)
        
        # Check if this exam belongs to the current instructor
        if exam.instructor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Check if there are any submissions for this exam
        submissions = StudentSubmission.query.filter_by(uploaded_exam_id=exam_id).all()
        if submissions:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete exam. There are {len(submissions)} student submission(s) for this exam. Please delete all submissions first.'
            }), 400
        
        # Delete the exam file from storage
        if exam.file_path and os.path.exists(exam.file_path):
            try:
                os.remove(exam.file_path)
            except Exception as e:
                print(f"Warning: Could not delete exam file {exam.file_path}: {e}")
        
        # Delete from database
        db.session.delete(exam)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Exam deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting exam: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@instructor_bp.route('/instructor/submission/<int:submission_id>/delete', methods=['POST'])
@login_required
def delete_submission(submission_id):
    """Delete a student submission"""
    if current_user.role != 'instructor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        submission = StudentSubmission.query.get_or_404(submission_id)
        
        # Check if this submission belongs to an exam owned by the current instructor
        exam = UploadedExam.query.get(submission.uploaded_exam_id)
        if not exam or exam.instructor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Delete submission files from storage
        if submission.submission_file_path and os.path.exists(submission.submission_file_path):
            try:
                os.remove(submission.submission_file_path)
            except Exception as e:
                print(f"Warning: Could not delete submission file {submission.submission_file_path}: {e}")
        
        # Delete question answers
        question_answers = QuestionAnswer.query.filter_by(student_submission_id=submission_id).all()
        for qa in question_answers:
            db.session.delete(qa)
        
        # Delete the submission
        db.session.delete(submission)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Submission deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting submission: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@instructor_bp.route('/instructor/exam/<int:exam_id>')
@login_required
def view_exam(exam_id):
    """View details of an uploaded exam"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    uploaded_exam = UploadedExam.query.get_or_404(exam_id)
    
    # Check if this exam belongs to the current instructor
    if uploaded_exam.instructor_id != current_user.id:
        flash('Access denied. You can only view your own exams.', 'error')
        return redirect(url_for('instructor.exams'))
    
    # Get student submissions for this exam
    submissions = StudentSubmission.query.filter_by(uploaded_exam_id=exam_id).order_by(StudentSubmission.submitted_at.desc()).all()
    
    return render_template('instructor/view_exam.html', 
                         uploaded_exam=uploaded_exam,
                         submissions=submissions)

@instructor_bp.route('/instructor/exam/<int:exam_id>/download')
@login_required
def download_exam(exam_id):
    """Download the original exam file"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    uploaded_exam = UploadedExam.query.get_or_404(exam_id)
    
    # Check if this exam belongs to the current instructor
    if uploaded_exam.instructor_id != current_user.id:
        flash('Access denied. You can only download your own exams.', 'error')
        return redirect(url_for('instructor.exams'))
    
    # Check if file exists
    if not os.path.exists(uploaded_exam.file_path):
        flash('Exam file not found.', 'error')
        return redirect(url_for('instructor.view_exam', exam_id=exam_id))
    
    try:
        return send_file(uploaded_exam.file_path, 
                        as_attachment=True, 
                        download_name=uploaded_exam.original_filename)
    except Exception as e:
        flash(f'Error downloading exam: {str(e)}', 'error')
        return redirect(url_for('instructor.view_exam', exam_id=exam_id))

@instructor_bp.route('/instructor/exam/<int:exam_id>/process', methods=['POST'])
@login_required
def process_exam(exam_id):
    """Process an uploaded exam to extract questions"""
    if current_user.role != 'instructor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    uploaded_exam = UploadedExam.query.get_or_404(exam_id)
    
    # Check if this exam belongs to the current instructor
    if uploaded_exam.instructor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Update status to processing
        uploaded_exam.processing_status = 'processing'
        db.session.commit()
        
        print(f"🔄 Processing exam: {uploaded_exam.title}")
        
        # Extract text from the uploaded exam file
        exam_text = extract_text_from_file(uploaded_exam.file_path, uploaded_exam.file_type)
        
        if not exam_text or exam_text.startswith("Error extracting text"):
            # If text extraction failed, use a fallback
            exam_text = "Exam content could not be extracted. Please manually review the uploaded file."
        
        print(f"📄 Extracted text length: {len(exam_text)} characters")
        
        # Initialize the DeepSeek AI grader for question extraction
        grader = ExamGrader(DEEPSEEK_API_KEY)
        
        # Use AI to extract questions from the exam content
        questions = extract_questions_with_ai(exam_text, grader)
        
        print(f"✅ Extracted {len(questions)} questions")
        for i, q in enumerate(questions, 1):
            print(f"  Q{i}: {q.get('text', '')[:100]}... ({q.get('max_points', 0)} points)")
        
        # Calculate total points
        total_points = sum(q.get('max_points', 10) for q in questions)
        
        # Create processing result
        processing_result = {
            'questions': questions,
            'total_questions': len(questions),
            'total_points': total_points,
            'extracted_text': exam_text[:500] + "..." if len(exam_text) > 500 else exam_text  # Truncate for storage
        }
        
        uploaded_exam.processing_status = 'completed'
        uploaded_exam.is_processed = True
        uploaded_exam.processing_result = json.dumps(processing_result)
        uploaded_exam.total_questions = processing_result['total_questions']
        uploaded_exam.total_points = processing_result['total_points']
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Exam processed successfully! Extracted {len(questions)} questions with {total_points} total points.',
            'questions': processing_result['questions'],
            'total_points': total_points
        })
        
    except Exception as e:
        print(f"❌ Error processing exam: {e}")
        uploaded_exam.processing_status = 'failed'
        db.session.commit()
        return jsonify({'success': False, 'error': str(e)}), 500

@instructor_bp.route('/instructor/submission/<int:submission_id>')
@login_required
def view_submission(submission_id):
    """View a student submission"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    submission = StudentSubmission.query.get_or_404(submission_id)
    uploaded_exam = UploadedExam.query.get(submission.uploaded_exam_id)
    
    # Check if this submission belongs to an exam by the current instructor
    if uploaded_exam.instructor_id != current_user.id:
        flash('Access denied. You can only view submissions for your own exams.', 'error')
        return redirect(url_for('instructor.exams'))
    
    # Get question answers for this submission
    question_answers = QuestionAnswer.query.filter_by(student_submission_id=submission_id).order_by(QuestionAnswer.question_number).all()
    
    return render_template('instructor/view_submission.html', 
                         submission=submission,
                         uploaded_exam=uploaded_exam,
                         question_answers=question_answers)

@instructor_bp.route('/instructor/submission/<int:submission_id>/download')
@login_required
def download_submission(submission_id):
    """Download a student submission file"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    submission = StudentSubmission.query.get_or_404(submission_id)
    uploaded_exam = UploadedExam.query.get(submission.uploaded_exam_id)
    
    # Check if this submission belongs to an exam by the current instructor
    if uploaded_exam.instructor_id != current_user.id:
        flash('Access denied. You can only download submissions for your own exams.', 'error')
        return redirect(url_for('instructor.exams'))
    
    # Check if file exists
    if not os.path.exists(submission.submission_file_path):
        flash('Submission file not found.', 'error')
        return redirect(url_for('instructor.view_submission', submission_id=submission_id))
    
    try:
        return send_file(submission.submission_file_path, 
                        as_attachment=True, 
                        download_name=submission.original_filename)
    except Exception as e:
        flash(f'Error downloading submission: {str(e)}', 'error')
        return redirect(url_for('instructor.view_submission', submission_id=submission_id))

@instructor_bp.route('/instructor/submission/<int:submission_id>/status', methods=['GET'])
@login_required
def get_grading_status(submission_id):
    """Get the current grading status of a submission"""
    if current_user.role != 'instructor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    submission = StudentSubmission.query.get_or_404(submission_id)
    uploaded_exam = UploadedExam.query.get(submission.uploaded_exam_id)
    
    # Check if this submission belongs to an exam by the current instructor
    if uploaded_exam.instructor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    return jsonify({
        'success': True,
        'submission_id': submission_id,
        'status': submission.grading_status,
        'is_graded': submission.is_graded,
        'total_score': submission.total_score if submission.is_graded else None,
        'max_score': submission.max_score if submission.is_graded else None,
        'graded_at': submission.graded_at.isoformat() if submission.graded_at else None
    })

@instructor_bp.route('/instructor/submission/<int:submission_id>/grade', methods=['POST'])
@login_required
def grade_submission(submission_id):
    """Grade a student submission using AI"""
    if current_user.role != 'instructor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    submission = StudentSubmission.query.get_or_404(submission_id)
    uploaded_exam = UploadedExam.query.get(submission.uploaded_exam_id)
    
    # Check if this submission belongs to an exam by the current instructor
    if uploaded_exam.instructor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Update status to grading
        submission.grading_status = 'grading'
        db.session.commit()
        
        # Get question answers for this submission
        question_answers = QuestionAnswer.query.filter_by(student_submission_id=submission_id).all()
        
        # If no question answers exist, create them from the exam processing result
        if not question_answers and uploaded_exam.processing_result:
            try:
                processing_data = json.loads(uploaded_exam.processing_result)
                questions = processing_data.get('questions', [])
                
                # Create question answers for each question
                for question_data in questions:
                    question_answer = QuestionAnswer(
                        student_submission_id=submission_id,
                        question_number=question_data.get('number', 1),
                        question_text=question_data.get('text', 'Question'),
                        answer_text="Student answer will be extracted from submission file",  # Will be updated during grading
                        max_score=question_data.get('max_points', 10),
                        score=0,
                        feedback="",
                        confidence_score=0.0
                    )
                    db.session.add(question_answer)
                
                db.session.commit()
                
                # Get the newly created question answers
                question_answers = QuestionAnswer.query.filter_by(student_submission_id=submission_id).all()
                
            except Exception as e:
                print(f"Error creating question answers: {e}")
                # If we can't create from processing result, return error
                return jsonify({
                    'success': False,
                    'error': f'Failed to process exam questions: {str(e)}'
                }), 500
        
        total_score = 0
        max_score = 0
        
        # Initialize grading system
        print("🚀 Initializing DeepSeek AI grading system...")
        try:
            # Test DeepSeek connection
            from src.services.grader.exam_grader import ExamGrader
            test_grader = ExamGrader()
            test_result = test_grader.test_api_connection()
            if test_result.get('status') == 'success':
                grader_available = True
                model_type = "deepseek_api"
                print("✅ DeepSeek AI grading system initialized successfully")
            else:
                grader_available = False
                model_type = "smart_fallback"
                print("⚠️ DeepSeek API not available, using fallback grading")
        except Exception as e:
            print(f"⚠️ Failed to initialize DeepSeek grading: {e}")
            grader_available = False
            model_type = "smart_fallback"
        
        # Extract text from the submission file for grading
        submission_text = ""
        try:
            if submission.submission_file_path and os.path.exists(submission.submission_file_path):
                # Extract text from the submission file using the same helper function
                submission_text = extract_text_from_file(submission.submission_file_path, submission.file_type)
                
                if not submission_text or submission_text.startswith("Error extracting text"):
                    submission_text = "Student answer content could not be extracted from the submission file."
                else:
                    print(f"✅ Extracted {len(submission_text)} characters from submission file")
            else:
                submission_text = "Submission file not found."
        except Exception as e:
            print(f"Error extracting text from submission file: {e}")
            submission_text = "Student answer content could not be extracted."
        
        # Process each question with timeout protection
        for i, qa in enumerate(question_answers):
            print(f"📝 Grading question {i+1}/{len(question_answers)}: {qa.question_number}")
            
            # Set a default max_score if it's 0
            if qa.max_score == 0:
                qa.max_score = 10  # Default 10 points per question
            
            # Use the individual answer text that was saved for this question
            question_answer = qa.answer_text if qa.answer_text else "No answer provided"
            
            # If no individual answer text, try to extract from submission file
            if not qa.answer_text or qa.answer_text == "No answer provided":
                question_answer = extract_answer_for_question(submission_text, qa.question_number, qa.question_text)
                print(f"📝 Question {qa.question_number}: Using extracted answer (length: {len(question_answer)})")
                
                # Save the extracted answer for future reference
                qa.answer_text = question_answer
                db.session.commit()
            else:
                print(f"📝 Question {qa.question_number}: Using saved answer (length: {len(question_answer)})")
            
            try:
                # Use DeepSeek AI grading if available, otherwise fallback
                if grader_available:
                    # Use the DeepSeek grading function with timeout protection
                    import threading
                    import time
                    
                    # Windows-compatible timeout mechanism
                    result = None
                    timeout_occurred = False
                    
                    def grade_with_timeout():
                        nonlocal result, timeout_occurred
                        try:
                            # Use the proper DeepSeek grading function
                            score, feedback = grade_with_deepseek(
                                question_text=qa.question_text,
                                answer_text=question_answer,
                                max_points=qa.max_score
                            )
                            result = {"score": score, "feedback": feedback, "method": "deepseek_api"}
                        except Exception as e:
                            result = {"error": str(e)}
                        finally:
                            timeout_occurred = False
                    
                    # Start grading in a separate thread
                    grading_thread = threading.Thread(target=grade_with_timeout)
                    grading_thread.daemon = True
                    grading_thread.start()
                    
                    # Wait for completion or timeout (20 seconds - reduced for efficiency)
                    grading_thread.join(timeout=20)
                    
                    if grading_thread.is_alive():
                        print(f"⚠️ Grading timeout for question {qa.question_number}, using content-based fallback")
                        score, feedback = grade_with_fallback(qa.question_text, question_answer, qa.max_score)
                        qa.confidence_score = 0.6  # Higher confidence for improved fallback
                        qa.score = score
                        qa.feedback = feedback  # Remove "Timeout fallback:" prefix for cleaner feedback
                        qa.graded_at = datetime.utcnow()
                        total_score += score
                        max_score += qa.max_score
                        continue
                    
                    # Process the result if grading completed successfully
                    if result and not result.get('error'):
                        # Extract score and feedback from the result
                        score = result.get('score', 0)
                        feedback = result.get('feedback', 'No feedback provided')
                        method = result.get('method', 'unknown')
                        
                        # Set confidence based on the grading method
                        if method == 'deepseek_api':
                            qa.confidence_score = 0.9  # High confidence for DeepSeek AI grading
                        elif method == 'smart_fallback':
                            qa.confidence_score = 0.7  # Medium confidence for fallback grading
                        else:
                            qa.confidence_score = 0.5  # Lower confidence for unknown method
                    else:
                        # AI grading failed, use fallback
                        print(f"⚠️ AI grading failed for question {qa.question_number}, using content-based fallback")
                        score, feedback = grade_with_fallback(qa.question_text, question_answer, qa.max_score)
                        qa.confidence_score = 0.5
                        
                else:
                    # Use content-based fallback grading
                    score, feedback = grade_with_fallback(qa.question_text, question_answer, qa.max_score)
                    qa.confidence_score = 0.7
                
                qa.score = score
                qa.feedback = feedback
                qa.answer_text = question_answer  # Store the specific answer for this question
                qa.graded_at = datetime.utcnow()
                
                print(f"✅ Question {qa.question_number} graded: {score}/{qa.max_score} points")
                
            except Exception as e:
                # Fallback to content-based grading if AI grading fails
                print(f"❌ AI grading failed for question {qa.question_number}: {e}")
                score, feedback = grade_with_fallback(qa.question_text, question_answer, qa.max_score)
                qa.score = score
                qa.feedback = feedback  # Use clean feedback without error prefix
                qa.graded_at = datetime.utcnow()
                qa.confidence_score = 0.4
            
            total_score += qa.score
            max_score += qa.max_score
        
        submission.total_score = total_score
        submission.max_score = max_score
        submission.is_graded = True
        submission.grading_status = 'completed'
        
        db.session.commit()
        
        print(f"🎉 Grading completed! Total score: {total_score}/{max_score}")
        
        return jsonify({
            'success': True,
            'message': f'Submission graded successfully using {model_type}! Graded {len(question_answers)} questions.',
            'total_score': total_score,
            'max_score': max_score,
            'questions_graded': len(question_answers),
            'model_used': model_type
        })
        
    except Exception as e:
        print(f"❌ Grading failed: {e}")
        submission.grading_status = 'failed'
        db.session.commit()
        return jsonify({'success': False, 'error': str(e)}), 500

@instructor_bp.route('/instructor/submissions')
@login_required
def all_submissions():
    """View all student submissions across all exams"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    # Get all submissions for exams by this instructor
    submissions = StudentSubmission.query.join(UploadedExam).filter(
        UploadedExam.instructor_id == current_user.id
    ).order_by(StudentSubmission.submitted_at.desc()).all()
    
    return render_template('instructor/all_submissions.html', submissions=submissions)

@instructor_bp.route('/instructor/submission/<int:submission_id>/reevaluate', methods=['POST'])
@login_required
def reevaluate_submission(submission_id):
    """Re-evaluate a student submission that has already been graded"""
    if current_user.role != 'instructor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        submission = StudentSubmission.query.get_or_404(submission_id)
        
        # Check if this submission belongs to an exam owned by the current instructor
        exam = UploadedExam.query.get(submission.uploaded_exam_id)
        if not exam or exam.instructor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Check if submission is already graded
        if not submission.is_graded:
            return jsonify({'success': False, 'error': 'Submission is not graded yet. Please grade it first.'}), 400
        
        # Get all question answers for this submission
        question_answers = QuestionAnswer.query.filter_by(student_submission_id=submission_id).order_by(QuestionAnswer.question_number).all()
        
        if not question_answers:
            return jsonify({'success': False, 'error': 'No question answers found for this submission'}), 400
        
        # Reset grading status
        submission.grading_status = 'processing'
        submission.is_graded = False
        submission.total_score = 0
        submission.max_score = 0
        
        # Reset individual question scores
        for qa in question_answers:
            qa.score = 0
            qa.feedback = ""
            qa.graded_at = None
            qa.confidence_score = 0
        
        db.session.commit()
        
        # Now call the regular grading function to re-grade
        return grade_submission(submission_id)
        
    except Exception as e:
        db.session.rollback()
        print(f"Error re-evaluating submission: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@instructor_bp.route('/instructor/exam/<int:exam_id>/reevaluate_all', methods=['POST'])
@login_required
def reevaluate_all_submissions(exam_id):
    """Re-evaluate all submissions for a specific exam"""
    if current_user.role != 'instructor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        exam = UploadedExam.query.get_or_404(exam_id)
        
        # Check if this exam belongs to the current instructor
        if exam.instructor_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Get all graded submissions for this exam
        submissions = StudentSubmission.query.filter_by(
            uploaded_exam_id=exam_id,
            is_graded=True
        ).all()
        
        if not submissions:
            return jsonify({'success': False, 'error': 'No graded submissions found for this exam'}), 400
        
        reevaluated_count = 0
        failed_count = 0
        
        for submission in submissions:
            try:
                # Reset grading status
                submission.grading_status = 'processing'
                submission.is_graded = False
                submission.total_score = 0
                submission.max_score = 0
                
                # Reset individual question scores
                question_answers = QuestionAnswer.query.filter_by(student_submission_id=submission.id).all()
                for qa in question_answers:
                    qa.score = 0
                    qa.feedback = ""
                    qa.graded_at = None
                    qa.confidence_score = 0
                
                db.session.commit()
                
                # Re-grade the submission
                result = grade_submission(submission.id)
                if result.status_code == 200:
                    reevaluated_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"Error re-evaluating submission {submission.id}: {e}")
                failed_count += 1
                db.session.rollback()
        
        return jsonify({
            'success': True,
            'message': f'Re-evaluation completed! {reevaluated_count} submissions re-evaluated successfully, {failed_count} failed.',
            'reevaluated_count': reevaluated_count,
            'failed_count': failed_count,
            'total_submissions': len(submissions)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error re-evaluating all submissions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

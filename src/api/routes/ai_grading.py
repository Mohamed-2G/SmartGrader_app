"""
AI Grading Routes
Handles AI-powered grading functionality using DeepSeek API
"""

from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
import re
import os

from src.core.models import Answer, Question, db
from src.services.grader.exam_grader import ExamGrader

# Create Blueprint
ai_grading_bp = Blueprint('ai_grading', __name__)

def grade_with_deepseek(question_text, answer_text, max_points):
    """Grade answer using DeepSeek API"""
    try:
        # Initialize the DeepSeek grader
        grader = ExamGrader()
        
        # Create a simple rubric for grading
        rubric = f"Grade this answer on a scale of 0 to {max_points} points. Consider accuracy, completeness, relevance, and quality of explanation."
        
        # Use the DeepSeek grading system
        result = grader.grade_exam(
            student_answer=answer_text,
            rubric=rubric,
            max_points=max_points,
            question_text=question_text
        )
        
        # Extract score and feedback from the result
        score = result.get('score', 0)
        feedback = result.get('feedback', 'No feedback provided')
        
        return score, feedback
        
    except Exception as e:
        # If DeepSeek fails, use the fallback grading
        print(f"DeepSeek grading failed: {e}")
        return grade_with_fallback(question_text, answer_text, max_points)

def grade_with_fallback(question_text, answer_text, max_points):
    """Content-based fallback grading when AI services are unavailable"""
    try:
        import re
        
        # Clean the input
        answer_text = answer_text.strip()
        question_text = question_text.strip()
        
        if not answer_text:
            return 0, "No answer provided. Please attempt to answer the question."
        
        # Analyze the question type and expected content
        question_lower = question_text.lower()
        answer_lower = answer_text.lower()
        
        # Initialize score based on content analysis, not length
        score = 0
        feedback_parts = []
        
        # Check for common question types and grade accordingly
        if any(word in question_lower for word in ["what is", "define", "name", "identify"]):
            # Definition/identification questions
            if len(answer_text.split()) >= 3:  # At least a basic definition
                score = max_points * 0.7
                feedback_parts.append("Good basic definition provided.")
            elif len(answer_text.split()) >= 1:
                score = max_points * 0.4
                feedback_parts.append("Basic answer provided, but could be more detailed.")
            else:
                score = 0
                feedback_parts.append("No definition provided.")
                
        elif any(word in question_lower for word in ["explain", "describe", "discuss"]):
            # Explanation questions
            if len(answer_text.split()) >= 15:
                score = max_points * 0.8
                feedback_parts.append("Good explanation with reasonable detail.")
            elif len(answer_text.split()) >= 8:
                score = max_points * 0.6
                feedback_parts.append("Basic explanation provided, could be more comprehensive.")
            elif len(answer_text.split()) >= 3:
                score = max_points * 0.3
                feedback_parts.append("Brief explanation, needs more detail.")
            else:
                score = 0
                feedback_parts.append("No explanation provided.")
                
        elif any(word in question_lower for word in ["compare", "contrast"]):
            # Comparison questions
            comparison_words = ["however", "while", "whereas", "but", "on the other hand", "in contrast", "similarly", "both", "neither"]
            comparison_count = sum(1 for word in comparison_words if word in answer_lower)
            
            if comparison_count >= 2 and len(answer_text.split()) >= 20:
                score = max_points * 0.9
                feedback_parts.append("Good comparison with clear contrasts identified.")
            elif comparison_count >= 1 and len(answer_text.split()) >= 10:
                score = max_points * 0.7
                feedback_parts.append("Basic comparison provided.")
            elif len(answer_text.split()) >= 5:
                score = max_points * 0.4
                feedback_parts.append("Some comparison attempted, but needs more structure.")
            else:
                score = 0
                feedback_parts.append("No comparison provided.")
                
        elif any(word in question_lower for word in ["analyze", "evaluate", "assess"]):
            # Analysis questions
            analysis_words = ["because", "therefore", "thus", "consequently", "as a result", "this shows", "this indicates"]
            analysis_count = sum(1 for word in analysis_words if word in answer_lower)
            
            if analysis_count >= 2 and len(answer_text.split()) >= 25:
                score = max_points * 0.9
                feedback_parts.append("Good analysis with logical reasoning.")
            elif analysis_count >= 1 and len(answer_text.split()) >= 15:
                score = max_points * 0.7
                feedback_parts.append("Basic analysis provided.")
            elif len(answer_text.split()) >= 8:
                score = max_points * 0.4
                feedback_parts.append("Some analysis attempted, needs more reasoning.")
            else:
                score = 0
                feedback_parts.append("No analysis provided.")
                
        elif any(word in question_lower for word in ["calculate", "solve", "compute", "find"]):
            # Calculation/mathematical questions
            # Look for numbers and mathematical operations
            numbers = re.findall(r'\d+\.?\d*', answer_text)
            if numbers:
                score = max_points * 0.8
                feedback_parts.append("Calculation attempted with numerical answer.")
            else:
                score = max_points * 0.2
                feedback_parts.append("No calculation or numerical answer provided.")
                
        elif any(word in question_lower for word in ["list", "enumerate", "outline"]):
            # List questions
            list_indicators = ["1.", "2.", "3.", "a)", "b)", "c)", "-", "•", "*"]
            list_count = sum(1 for indicator in list_indicators if indicator in answer_text)
            
            if list_count >= 3:
                score = max_points * 0.9
                feedback_parts.append("Good list with multiple items provided.")
            elif list_count >= 1:
                score = max_points * 0.6
                feedback_parts.append("Some list items provided.")
            else:
                score = max_points * 0.3
                feedback_parts.append("No structured list provided.")
                
        else:
            # General questions - analyze content relevance
            # Check if answer contains key terms from the question
            question_words = set(re.findall(r'\b\w+\b', question_lower))
            answer_words = set(re.findall(r'\b\w+\b', answer_lower))
            common_words = question_words.intersection(answer_words)
            
            if len(common_words) >= 3 and len(answer_text.split()) >= 10:
                score = max_points * 0.8
                feedback_parts.append("Answer addresses the question with relevant content.")
            elif len(common_words) >= 1 and len(answer_text.split()) >= 5:
                score = max_points * 0.6
                feedback_parts.append("Some relevant content provided.")
            elif len(answer_text.split()) >= 3:
                score = max_points * 0.3
                feedback_parts.append("Basic response, but may not fully address the question.")
            else:
                score = 0
                feedback_parts.append("Answer does not appear to address the question.")
        
        # Ensure score doesn't exceed max points
        score = min(int(score), max_points)
        
        # Create comprehensive feedback
        if score == 0:
            feedback = "No meaningful answer provided. Please attempt to address the question."
        elif score < max_points * 0.5:
            feedback = f"Basic attempt made. {feedback_parts[0] if feedback_parts else 'Could improve with more detail and accuracy.'}"
        elif score < max_points * 0.8:
            feedback = f"Good effort. {feedback_parts[0] if feedback_parts else 'Answer shows understanding but could be more comprehensive.'}"
        else:
            feedback = f"Excellent answer. {feedback_parts[0] if feedback_parts else 'Well done!'}"
        
        feedback += f" (Fallback grading used - {score}/{max_points} points)"
        
        return score, feedback
        
    except Exception as e:
        return 0, f"Fallback grading error: {str(e)}"

@ai_grading_bp.route('/api/grade', methods=['POST'])
@login_required
def grade_answer():
    """Grade a single answer using AI"""
    try:
        data = request.get_json()
        answer_id = data.get('answer_id')
        
        if not answer_id:
            return jsonify({'success': False, 'error': 'Answer ID is required'}), 400
        
        # Get the answer and question
        answer = Answer.query.get_or_404(answer_id)
        question = Question.query.get(answer.question_id)
        
        # Check if user has permission to grade this answer
        # (Only instructors should be able to grade)
        if current_user.role != 'instructor':
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Try DeepSeek API as primary grading method
        try:
            score, feedback = grade_with_deepseek(
                question.question_text, 
                answer.answer_text, 
                question.points
            )
        except Exception as e:
            print(f"DeepSeek grading failed: {e}")
            # Fallback to content-based grading if DeepSeek fails
            score, feedback = grade_with_fallback(
                question.question_text, 
                answer.answer_text, 
                question.points
            )
        
        # Update the answer with the grade
        answer.score = score
        answer.feedback = feedback
        db.session.commit()
        
        return jsonify({
            'success': True,
            'score': score,
            'max_points': question.points,
            'feedback': feedback
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_grading_bp.route('/api/grade_batch', methods=['POST'])
@login_required
def grade_batch():
    """Grade multiple answers at once"""
    try:
        data = request.get_json()
        answer_ids = data.get('answer_ids', [])
        
        if not answer_ids:
            return jsonify({'success': False, 'error': 'Answer IDs are required'}), 400
        
        if current_user.role != 'instructor':
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        results = []
        
        for answer_id in answer_ids:
            try:
                answer = Answer.query.get(answer_id)
                if not answer:
                    results.append({'answer_id': answer_id, 'error': 'Answer not found'})
                    continue
                
                question = Question.query.get(answer.question_id)
                
                # Grade the answer using DeepSeek API
                try:
                    score, feedback = grade_with_deepseek(
                        question.question_text, 
                        answer.answer_text, 
                        question.points
                    )
                except Exception as e:
                    print(f"DeepSeek grading failed for answer {answer_id}: {e}")
                    score, feedback = grade_with_fallback(
                        question.question_text, 
                        answer.answer_text, 
                        question.points
                    )
                
                # Update the answer
                answer.score = score
                answer.feedback = feedback
                
                results.append({
                    'answer_id': answer_id,
                    'score': score,
                    'max_points': question.points,
                    'feedback': feedback
                })
                
            except Exception as e:
                results.append({'answer_id': answer_id, 'error': str(e)})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_grading_bp.route('/api/test_grading', methods=['POST'])
@login_required
def test_grading():
    """Test the grading system with sample text"""
    try:
        data = request.get_json()
        test_text = data.get('text', '')
        max_points = data.get('max_points', 20)
        
        if not test_text:
            return jsonify({'success': False, 'error': 'Test text is required'}), 400
        
        if current_user.role != 'instructor':
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Test the grading system with DeepSeek
        try:
            score, feedback = grade_with_deepseek(
                "Test question", 
                test_text, 
                max_points
            )
        except Exception as e:
            print(f"DeepSeek test grading failed: {e}")
            score, feedback = grade_with_fallback(
                "Test question", 
                test_text, 
                max_points
            )
        
        return jsonify({
            'success': True,
            'score': score,
            'max_points': max_points,
            'feedback': feedback,
            'model_used': 'DeepSeek AI' if 'DeepSeek' in feedback else 'Fallback'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_grading_bp.route('/test_grading')
@login_required
def test_grading_page():
    """Serve the test grading page"""
    if current_user.role != 'instructor':
        flash('Access denied. Instructors only.', 'error')
        return redirect(url_for('index'))
    
    return render_template('test_essay_model.html')

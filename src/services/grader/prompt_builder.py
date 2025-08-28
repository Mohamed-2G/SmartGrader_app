"""
Prompt construction module for SmartGrader.

This module provides functionality to format prompts for AI-based grading
by combining questions, rubrics, and student answers into structured prompts.
"""

from typing import Dict, Any, Optional


def format_grading_prompt(
    question: str,
    rubric: Dict[str, Any],
    student_answer: str,
    additional_instructions: Optional[str] = None
) -> str:
    """
    Format a prompt for AI-based grading from question, rubric, and student answer.
    
    Args:
        question: The question or prompt that was given to the student
        rubric: Dictionary containing the grading rubric with criteria and point values
        student_answer: The student's response to the question
        additional_instructions: Optional additional instructions for the AI grader
        
    Returns:
        Formatted prompt string ready for AI evaluation
    """
    
    # Start with the main instruction
    prompt_parts = [
        "You are an expert grader evaluating a student's response to an academic question.",
        "Please evaluate the student's answer based on the provided rubric and provide detailed feedback.",
        "",
        "QUESTION:",
        question,
        "",
        "STUDENT ANSWER:",
        student_answer,
        "",
        "GRADING RUBRIC:"
    ]
    
    # Format the rubric
    if isinstance(rubric, dict):
        for criterion, details in rubric.items():
            if isinstance(details, dict):
                # Handle detailed rubric format
                points = details.get('points', 0)
                description = details.get('description', '')
                prompt_parts.append(f"- {criterion} ({points} points): {description}")
            else:
                # Handle simple rubric format
                prompt_parts.append(f"- {criterion}: {details}")
    else:
        # Fallback for non-dict rubric
        prompt_parts.append(str(rubric))
    
    prompt_parts.append("")
    prompt_parts.append("EVALUATION INSTRUCTIONS:")
    prompt_parts.append("1. Evaluate each rubric criterion separately")
    prompt_parts.append("2. Provide specific feedback for each criterion")
    prompt_parts.append("3. Award points based on how well the answer meets each criterion")
    prompt_parts.append("4. Provide constructive feedback for improvement")
    prompt_parts.append("5. Calculate the total score")
    prompt_parts.append("")
    prompt_parts.append("Please provide your evaluation in the following format:")
    prompt_parts.append("- Criterion 1: [score]/[max points] - [feedback]")
    prompt_parts.append("- Criterion 2: [score]/[max points] - [feedback]")
    prompt_parts.append("...")
    prompt_parts.append("- Total Score: [total]/[max total]")
    prompt_parts.append("- Overall Feedback: [comprehensive feedback]")
    
    # Add any additional instructions
    if additional_instructions:
        prompt_parts.append("")
        prompt_parts.append("ADDITIONAL INSTRUCTIONS:")
        prompt_parts.append(additional_instructions)
    
    return "\n".join(prompt_parts)


def format_simple_grading_prompt(
    question: str,
    rubric: Dict[str, Any],
    student_answer: str
) -> str:
    """
    Format a simplified prompt for quick grading.
    
    Args:
        question: The question or prompt that was given to the student
        rubric: Dictionary containing the grading rubric
        student_answer: The student's response to the question
        
    Returns:
        Simplified formatted prompt string
    """
    
    prompt = f"""Please grade this student's answer based on the rubric:

Question: {question}

Student Answer: {student_answer}

Rubric: {rubric}

Please provide a score and brief feedback."""

    return prompt


def format_detailed_grading_prompt(
    question: str,
    rubric: Dict[str, Any],
    student_answer: str,
    context: Optional[str] = None
) -> str:
    """
    Format a detailed prompt for comprehensive grading with additional context.
    
    Args:
        question: The question or prompt that was given to the student
        rubric: Dictionary containing the grading rubric
        student_answer: The student's response to the question
        context: Optional additional context about the assignment or course
        
    Returns:
        Detailed formatted prompt string
    """
    
    prompt_parts = [
        "You are an expert academic grader with deep knowledge in the subject matter.",
        "Your task is to provide a comprehensive evaluation of the student's response.",
        "",
        "ASSIGNMENT CONTEXT:"
    ]
    
    if context:
        prompt_parts.append(context)
    else:
        prompt_parts.append("Standard academic evaluation")
    
    prompt_parts.extend([
        "",
        "QUESTION:",
        question,
        "",
        "STUDENT ANSWER:",
        student_answer,
        "",
        "DETAILED RUBRIC:"
    ])
    
    # Format detailed rubric
    total_points = 0
    for criterion, details in rubric.items():
        if isinstance(details, dict):
            points = details.get('points', 0)
            description = details.get('description', '')
            total_points += points
            prompt_parts.append(f"- {criterion} ({points} points)")
            prompt_parts.append(f"  Description: {description}")
        else:
            prompt_parts.append(f"- {criterion}: {details}")
    
    prompt_parts.extend([
        "",
        f"TOTAL POSSIBLE POINTS: {total_points}",
        "",
        "EVALUATION REQUIREMENTS:",
        "1. Analyze each rubric criterion thoroughly",
        "2. Provide specific, actionable feedback for each criterion",
        "3. Award points based on demonstrated understanding and quality",
        "4. Identify strengths and areas for improvement",
        "5. Provide constructive suggestions for enhancement",
        "6. Ensure fair and consistent grading",
        "",
        "RESPONSE FORMAT:",
        "Please structure your response as follows:",
        "",
        "CRITERION EVALUATIONS:",
        "[For each criterion, provide: score/max_points - detailed feedback]",
        "",
        "TOTAL SCORE: [total]/[max_total]",
        "",
        "OVERALL ASSESSMENT:",
        "[Comprehensive evaluation of the answer's strengths and weaknesses]",
        "",
        "RECOMMENDATIONS:",
        "[Specific suggestions for improvement]"
    ])
    
    return "\n".join(prompt_parts)
def format_json_grading_prompt(
    question: str,
    rubric: Dict[str, Any],
    student_answer: str,
    context: Optional[str] = None
) -> str:
    """
    Format a prompt instructing GPT to return structured JSON output for grading.

    Returns:
        A prompt that requests JSON with fields: score, max_score, feedback
    """
    if context is None:
        context = "Standard academic grading"

    rubric_text = "\n".join([
        f"- {k}: {v['description']} ({v['points']} point{'s' if v['points'] != 1 else ''})"
        for k, v in rubric.items()
        if isinstance(v, dict)
    ])

    total_points = sum(v.get('points', 0) for v in rubric.values() if isinstance(v, dict))

    prompt = f"""
You are an AI academic assistant trained to grade student responses based on a rubric.

Context: {context}

Question:
{question}

Student Answer:
{student_answer}

Rubric Criteria:
{rubric_text}

Instructions:
- Carefully evaluate the student's answer.
- For each rubric criterion, assign partial or full points.
- Return only a valid JSON object with the following keys:
    - "score": total score awarded (numeric)
    - "max_score": maximum possible score (numeric)
    - "feedback": a concise but clear explanation justifying the grade

Format your response **only** as JSON like this:

{{
  "score": <numeric>,
  "max_score": {total_points},
  "feedback": "<your explanation here>"
}}
"""
    return prompt.strip()

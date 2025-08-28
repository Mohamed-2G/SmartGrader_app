import fitz  # PyMuPDF for PDF processing
from pytesseract import image_to_string
from PIL import Image
import openai
import os

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_text_from_file(file_path, file_type):
    """Extract text content from different file types"""
    try:
        if file_type == 'pdf':
            return extract_text_from_pdf(file_path)
        
        elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
            return extract_text_from_image(file_path)
        
        elif file_type in ['txt', 'doc', 'docx', 'text']:
            # For text files, read directly
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read().strip()
        
        else:
            return f"Unsupported file type: {file_type}. Supported types: PDF, images (JPG, PNG, GIF, BMP, TIFF), and text files (TXT, DOC, DOCX)"
            
    except Exception as e:
        return f"Error extracting text from {file_type} file: {str(e)}"

def extract_text_from_pdf(file_path):
    """Extract text from PDF using PyMuPDF with improved formatting for question detection"""
    try:
        doc = fitz.open(file_path)
        text = ""
        
        for page_num, page in enumerate(doc):
            # Get text with better formatting
            page_text = page.get_text("text")
            
            # Clean up the text
            page_text = page_text.strip()
            
            # Add page separator if not empty
            if page_text:
                if text:  # If not the first page, add a separator
                    text += "\n\n--- Page " + str(page_num + 1) + " ---\n\n"
                else:  # First page
                    text += "--- Page " + str(page_num + 1) + " ---\n\n"
                text += page_text
        
        # Clean up the final text
        text = text.strip()
        
        # Remove excessive whitespace while preserving structure
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:  # Only add non-empty lines
                cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Improve question detection by preserving numbering patterns
        # Look for common question patterns and ensure they're properly formatted
        import re
        
        # Fix common numbering issues
        # Convert "1." to "1." (ensure proper spacing)
        text = re.sub(r'(\d+)\.\s*', r'\1. ', text)
        
        # Fix "Question X:" patterns
        text = re.sub(r'Question\s+(\d+)\s*:', r'Question \1: ', text)
        
        # Fix "Q." patterns
        text = re.sub(r'Q\.?\s*(\d+)\s*:', r'Q\1: ', text)
        
        # Ensure proper spacing after question numbers
        text = re.sub(r'(\d+)\)\s*', r'\1) ', text)
        
        # Fix lettered questions
        text = re.sub(r'([a-z])\.\s*', r'\1. ', text, flags=re.IGNORECASE)
        
        return text if text else "No text content found in PDF"
        
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

def extract_text_from_image(file_path):
    """Extract text from image using OCR (pytesseract)"""
    try:
        # Check if tesseract is available
        import pytesseract
        try:
            # Try to get tesseract version to check if it's installed
            pytesseract.get_tesseract_version()
        except Exception:
            return ("Tesseract is not installed or not found in PATH. "
                   "Please install Tesseract OCR:\n"
                   "1. Download from: https://github.com/UB-Mannheim/tesseract/wiki\n"
                   "2. Install to default location (C:\\Program Files\\Tesseract-OCR)\n"
                   "3. Add to PATH or restart your terminal\n"
                   "Alternative: Use 'choco install tesseract' if you have Chocolatey")
        
        with Image.open(file_path) as img:
            text = image_to_string(img)
        
        if not text.strip():
            return "No text was detected in the image. Please ensure the image contains clear, readable text."
        
        return text
    except Exception as e:
        return f"Error extracting text from image: {str(e)}"

def process_file_with_ai(file_path, file_type, question_text, openai_api_key):
    """Process uploaded file with AI for grading"""
    try:
        # Extract text based on file type
        if file_type == 'pdf':
            extracted_text = extract_text_from_pdf(file_path)
        elif file_type in ['image', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
            extracted_text = extract_text_from_image(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()

        prompt = (
            f"You are an expert grader evaluating a student's response to an academic question.\n"
            f"QUESTION: {question_text}\n"
            f"STUDENT RESPONSE (extracted from {file_type.upper()} file):\n{extracted_text}\n"
            "Please evaluate this response and provide:\n"
            "1. A score out of 20\n"
            "2. Detailed feedback on the content\n"
            "3. Comments on handwriting/formatting (if applicable)\n"
            "4. Suggestions for improvement\n"
            "Format your response as JSON:\n"
            "{\n"
            "  \"score\": <number>,\n"
            "  \"feedback\": \"<detailed feedback>\",\n"
            "  \"handwriting_comments\": \"<comments on handwriting/formatting>\",\n"
            "  \"suggestions\": \"<improvement suggestions>\"\n"
            "}"
        )

        openai.api_key = openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error processing file with AI: {str(e)}"

"""
helpers.py - Utility functions for SmartGrader
"""

def get_security_questions():
    """Get list of available security questions"""
    return [
        "What was the name of your first pet?",
        "In which city were you born?",
        "What was your mother's maiden name?",
        "What was the name of your first school?",
        "What is your favorite color?",
        "What was the make of your first car?",
        "What is the name of the street you grew up on?",
        "What is your favorite movie?",
        "What is the name of your favorite teacher?",
        "What is your favorite food?"
    ]

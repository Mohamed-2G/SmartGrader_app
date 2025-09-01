import fitz  # PyMuPDF for PDF processing
from pytesseract import image_to_string
from PIL import Image
from io import BytesIO
# import openai  # Removed - not used in current implementation
# Removed os import - no longer needed for filesystem operations

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def _normalize_extracted_text(raw_text: str) -> str:
    """Normalize and clean extracted text similarly for both file and bytes paths."""
    try:
        text = raw_text.strip()
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)
        
        # Improve question detection by preserving numbering patterns
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
        
        return text if text else "No text content found"
        
    except Exception as e:
        return f"Error normalizing text: {str(e)}"

def extract_text_from_pdf_bytes(file_data: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF with improved formatting for question detection"""
    try:
        doc = fitz.open(stream=file_data, filetype="pdf")
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
        
        doc.close()
        return _normalize_extracted_text(text)
        
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

def extract_text_from_image_bytes(file_data: bytes) -> str:
    """Extract text from image bytes using OCR with improved preprocessing"""
    try:
        # Open image from bytes
        with Image.open(BytesIO(file_data)) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large (OCR works better with reasonable sizes)
            max_size = 2000
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Extract text using OCR
            text = image_to_string(img, config='--psm 6 --oem 3')
            
            return _normalize_extracted_text(text)
            
    except Exception as e:
        return f"Error extracting text from image: {str(e)}"

def extract_text_from_text_bytes(file_data: bytes) -> str:
    """Extract text from text file bytes"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                text = file_data.decode(encoding)
                return _normalize_extracted_text(text)
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, try with error handling
        text = file_data.decode('utf-8', errors='ignore')
        return _normalize_extracted_text(text)
        
    except Exception as e:
        return f"Error extracting text from text file: {str(e)}"

def extract_text_from_any(file_data: bytes | None, file_type: str) -> str:
    """
    Extract text from file data bytes.
    
    Args:
        file_data: Raw file bytes
        file_type: Type of file (pdf, image, text, etc.)
    
    Returns:
        Extracted text as string
    """
    if not file_data:
        return "No file data provided"
    
    # Normalize file type
    normalized_type = file_type.lower()
    
    try:
        if normalized_type == 'pdf':
            return extract_text_from_pdf_bytes(file_data)
        
        elif normalized_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'image']:
            return extract_text_from_image_bytes(file_data)
        
        elif normalized_type in ['txt', 'doc', 'docx', 'document', 'text']:
            return extract_text_from_text_bytes(file_data)
        
        else:
            return f"Unsupported file type: {file_type}. Supported types: PDF, images (JPG, PNG, GIF, BMP, TIFF), and text files (TXT, DOC, DOCX)"
            
    except Exception as e:
        return f"Error extracting text from {file_type} file: {str(e)}"

# def process_file_with_ai(file_data: bytes, file_type: str, question_text: str, openai_api_key: str):
#     """Process a file with AI to answer a specific question - LEGACY FUNCTION NOT USED"""
#     # This function is commented out as it's not used in the current implementation
#     # The main grading system uses DeepSeek API instead of OpenAI
#     return "This function is not available in the current implementation"

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

def extract_text_from_pdf(file_path):
    """Legacy function for backward compatibility - redirects to bytes version"""
    # This function is kept for backward compatibility
    # New code should use extract_text_from_pdf_bytes directly
    return "This function is deprecated. Use extract_text_from_pdf_bytes instead."

def extract_text_from_image(file_path):
    """Legacy function for backward compatibility - redirects to bytes version"""
    # This function is kept for backward compatibility
    # New code should use extract_text_from_image_bytes directly
    return "This function is deprecated. Use extract_text_from_image_bytes instead."

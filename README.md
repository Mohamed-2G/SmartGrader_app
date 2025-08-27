# 🎓 SmartGrader - AI-Powered Exam Grading System

SmartGrader is a comprehensive web application that uses DeepSeek's AI API to automatically grade student exam submissions. The system provides intelligent feedback, supports multiple file formats, and offers a complete workflow for instructors and students.

## ✨ Features

### 🤖 **AI-Powered Grading**
- **DeepSeek AI API**: Uses DeepSeek's advanced language model for intelligent grading
- **Smart Fallback System**: Robust grading even when AI models are unavailable
- **Individual Question Grading**: Each answer is graded against its specific question
- **Detailed Feedback**: Comprehensive, constructive feedback for students
- **Confidence Scoring**: AI confidence levels for grading accuracy

### 📝 **Exam Management**
- **PDF Upload & Processing**: Automatic question extraction from PDF exams
- **Manual Question Creation**: Add questions manually for better control
- **Multiple Question Formats**: Supports various question numbering styles
- **Point Assignment**: Flexible point allocation per question
- **Exam Organization**: Categorize exams by subject and description

### 👨‍🏫 **Instructor Features**
- **Dashboard**: Overview of all exams and submissions
- **Submission Management**: View, grade, and manage student submissions
- **Re-evaluation**: Re-grade submissions with updated criteria
- **Bulk Operations**: Re-evaluate all submissions for an exam
- **Delete Management**: Remove exams and submissions as needed
- **Download Options**: Download exam files and student submissions

### 👨‍🎓 **Student Features**
- **Exam Access**: View available exams with clear instructions
- **Multiple Submission Methods**: 
  - Individual text answers per question
  - Individual file uploads per question
  - Complete answer file upload (PDF/image)
- **Smart Answer Detection**: Automatic extraction and matching of answers
- **Progress Tracking**: View submission history and grades
- **Detailed Results**: See individual question scores and feedback

### 📄 **File Support**
- **Exam Files**: PDF documents with automatic question extraction
- **Student Submissions**: PDF, images (JPG, PNG, GIF, BMP, TIFF), text files
- **OCR Processing**: Handwritten answer recognition using Tesseract
- **Text Extraction**: Advanced PDF text extraction with formatting preservation

### 🔒 **Security & User Management**
- **Role-Based Access**: Separate interfaces for instructors and students
- **User Authentication**: Secure login system
- **File Validation**: Secure file upload handling
- **Data Protection**: Proper file storage and access controls

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- DeepSeek API key
- Tesseract OCR (for image processing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SmartGrader
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

3. **Configure environment variables**
   ```bash
   # Edit .env file with your DeepSeek API key
   DEEPSEEK_API_KEY=your_deepseek_token_here
   ```

4. **Start the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open http://localhost:5000 in your browser
   - Login with default credentials:
     - Instructor: `teacher` / `password`
     - Student: `student` / `password`
     - Admin: `admin` / `password`

## 📋 System Requirements

### Software Dependencies
- **Python 3.8+**: Core runtime
- **Flask 3.0+**: Web framework
- **Requests**: HTTP library for API calls
- **PyMuPDF**: PDF processing
- **Tesseract OCR**: Image text recognition

### Hardware Requirements
- **RAM**: Minimum 4GB (8GB recommended for optimal performance)
- **Storage**: 2GB free space for uploads
- **Internet**: Required for API calls

### Model Requirements
- **DeepSeek API**: Cloud-based AI model (no local storage required)
- **Internet**: Required for API calls

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
# Required
DEEPSEEK_API_KEY=your_deepseek_token_here

# Optional
DATABASE_URL=sqlite:///site.db
UPLOAD_FOLDER=uploads
SECRET_KEY=your_secret_key_here
SMTP_EMAIL=noreply@smartgrader.com
SMTP_PASSWORD=your_email_password
DEEPSEEK_API_KEY=your_deepseek_key_here
```

### Tesseract OCR Setup
For image processing capabilities:

**Windows:**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location
3. Add to PATH or restart terminal

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

## 📖 Usage Guide

### For Instructors

1. **Upload an Exam**
   - Go to "Upload Exam" in the instructor dashboard
   - Upload a PDF file containing exam questions
   - Choose between automatic processing or manual question creation
   - Set subject and description

2. **Process Questions**
   - Automatic: System extracts questions using AI
   - Manual: Add questions one by one with custom points
   - Review and edit extracted questions as needed

3. **Monitor Submissions**
   - View all student submissions in the exam dashboard
   - See submission status (pending, processing, graded)
   - Access individual submission details

4. **Grade Submissions**
   - Click "Grade Submission" for automatic AI grading
   - Review scores and feedback
   - Use "Re-evaluate" to re-grade if needed
   - Bulk re-evaluate all submissions for an exam

### For Students

1. **Take an Exam**
   - Browse available exams in the student dashboard
   - Click "Take Exam" to start
   - Read questions and instructions carefully

2. **Submit Answers**
   - **Method 1**: Type answers in individual text boxes
   - **Method 2**: Upload individual files for each question
   - **Method 3**: Upload a complete answer file (recommended)
   - Ensure answers are clearly numbered for automatic detection

3. **View Results**
   - Check submission status
   - View detailed scores and feedback
   - Download submission files

## 🧪 Testing

Run the test suite to verify system functionality:

```bash
# Test phi model grading
python test_phi_grading.py

# Test complete system
python -m pytest tests/
```

## 🔍 Troubleshooting

### Common Issues

**Model Loading Errors:**
- Ensure sufficient RAM (8GB+)
- Check model files are complete in `models/phi-3.5-mini-instruct/`
- Verify HuggingFace API key is valid

**File Upload Issues:**
- Check file size limits
- Verify file format is supported
- Ensure upload directory has write permissions

**OCR Processing:**
- Install Tesseract OCR
- Add Tesseract to system PATH
- Restart application after installation

**Database Issues:**
- Delete `site.db` to reset database
- Check database file permissions
- Verify SQLite is working

### Performance Optimization

**For Better Speed:**
- Use GPU acceleration if available
- Increase system RAM
- Optimize model loading with caching

**For Better Accuracy:**
- Use clear, well-formatted exam PDFs
- Ensure student answers are properly numbered
- Provide detailed grading rubrics

## 🏗️ Architecture

### Core Components
- **Flask Web Framework**: Main application server
- **SQLAlchemy ORM**: Database management
- **Phi-3.5-mini-instruct**: Local AI grading model
- **PyMuPDF**: PDF processing and text extraction
- **Tesseract OCR**: Image text recognition

### File Structure
```
SmartGrader/
├── app.py                 # Main application entry point
├── config.py             # Configuration settings
├── models.py             # Database models
├── grader/
│   └── exam_grader.py    # AI grading engine
├── routes/
│   ├── instructor.py     # Instructor routes
│   └── student.py        # Student routes
├── templates/            # HTML templates
├── static/              # CSS, JS, images
├── models/              # AI model files
├── uploads/             # File uploads
└── requirements.txt     # Python dependencies
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Microsoft**: For the Phi-3.5-mini-instruct model
- **HuggingFace**: For the transformers library
- **Flask**: For the web framework
- **PyMuPDF**: For PDF processing capabilities

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the documentation

---

**SmartGrader** - Making exam grading intelligent, efficient, and fair! 🎓✨ 
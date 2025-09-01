# SmartGrader - AI-Powered Exam Grading System

A comprehensive Flask-based web application that automates exam grading using AI, with support for multiple user roles, file uploads, and intelligent question extraction.

## Features

### Core Functionality
- **AI-Powered Grading**: Uses DeepSeek API for intelligent exam grading with fallback mechanisms
- **Database Storage**: All files (PDFs, images, documents) are stored directly in SQLite database as BLOBs
- **Automatic Question Extraction**: AI extracts questions from uploaded exam files
- **Multi-Role Support**: Instructor, Student, and Moderator interfaces
- **Multi-Language Support**: English, French, Arabic, and Turkish

### User Roles

#### Instructor
- Upload exams (PDF, images, documents)
- Automatic question extraction using AI
- View and grade student submissions
- Manage exam content and settings
- Download student submissions

#### Student
- View available exams
- Submit answers (text or file uploads)
- View grading results and feedback
- Access submission history

#### Moderator
- User management (create, edit, delete users)
- System settings configuration
- Access to all instructor and student features
- Database administration

### Technical Features
- **File Processing**: Supports PDF, images (PNG, JPG, GIF), and text documents
- **AI Integration**: DeepSeek API for question extraction and grading
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Flask-Login with role-based access control
- **Responsive UI**: Modern web interface with Bootstrap

## 🛠Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SmartGrader
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_secret_key_here
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   GMAIL_USER=your_email@gmail.com
   GMAIL_PASS=your_app_password
   ```

4. **Initialize the database**
   ```bash
   flask db init
   flask db migrate -m "initial migration"
   flask db upgrade
   ```

5. **Run the application**
   ```bash
   flask run --debug
   ```

## Project Structure

```
SmartGrader/
├── app.py                          # Main Flask application
├── src/
│   ├── core/
│   │   ├── config.py              # Configuration settings
│   │   ├── extensions.py          # Flask extensions
│   │   └── models.py              # Database models
│   ├── api/
│   │   └── routes/
│   │       ├── instructor.py      # Instructor routes
│   │       ├── student.py         # Student routes
│   │       ├── moderator.py       # Moderator routes
│   │       ├── ai_grading.py      # AI grading routes
│   │       └── auth.py            # Authentication routes
│   ├── services/
│   │   └── grader/
│   │       ├── exam_grader.py     # Exam grading service
│   │       └── prompt_builder.py  # AI prompt construction
│   └── utils/
│       ├── helpers.py             # Utility functions
│       └── translations.py        # Multi-language support
├── templates/                      # HTML templates
├── static/                        # CSS, JS, and static assets
└── instance/                      # Database files
```

## 🗄️ Database Models

### Core Models
- **User**: User accounts with role-based access
- **UploadedExam**: Exam files and metadata
- **StudentSubmission**: Student answer submissions
- **QuestionAnswer**: Individual question responses and grades
- **Message**: User-to-user messaging system
- **SystemSettings**: Application configuration

### Key Features
- **BLOB Storage**: All files stored as binary data in database
- **JSON Processing**: Exam questions stored as structured JSON
- **Audit Trail**: Timestamps and user tracking for all operations

## 🔧 Configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key for sessions
- `DEEPSEEK_API_KEY`: API key for DeepSeek AI services
- `GMAIL_USER`: Gmail username for email functionality
- `GMAIL_PASS`: Gmail app password

### File Types Supported
- **PDF**: Text extraction using PyMuPDF
- **Documents**: Direct text reading
- **Manual**: Text-based question creation

## Usage

### For Instructors
1. **Login** with instructor credentials
2. **Upload Exam** by selecting a file or creating questions manually
3. **Process Exam** to extract questions using AI
4. **View Submissions** from students
5. **Grade Submissions** using AI grading system

### For Students
1. **Login** with student credentials
2. **View Available Exams** from the dashboard
3. **Take Exam** by answering questions or uploading files
4. **View Results** and feedback after grading

### For Moderators
1. **Login** with moderator credentials
2. **Manage Users** (create, edit, delete)
3. **Configure System** settings
4. **Access All Features** available to instructors and students

## Security Features

- **Role-Based Access Control**: Users can only access features appropriate to their role
- **Session Management**: Secure session handling with Flask-Login
- **File Validation**: Secure filename handling and type validation
- **Database Integrity**: SQLAlchemy with proper error handling

## Testing

### Default Users
The system creates default users on first run:
- **Admin**: `admin` / `admin12` (moderator role)
- **Instructor**: `teacher` / `teacher12` (instructor role)
- **Student**: `student` / `student12` (student role)

### Testing Features
- Upload various file types
- Test AI question extraction
- Submit student answers
- Test AI grading system
- Verify role-based access

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure all dependencies are installed
2. **Database Errors**: Run `flask db upgrade` to apply migrations
3. **API Errors**: Verify DeepSeek API key is set correctly
4. **File Upload Issues**: Check file size and type restrictions

### Debug Mode
Run with debug mode for detailed error information:
```bash
flask run --debug
```

## API Endpoints

### Authentication
- `POST /login` - User login
- `POST /register` - User registration
- `GET /logout` - User logout

### Instructor Routes
- `GET /instructor/dashboard` - Instructor dashboard
- `POST /instructor/upload_exam` - Upload exam file
- `POST /instructor/exam/<id>/process` - Process exam with AI
- `GET /instructor/submission/<id>` - View student submission

### Student Routes
- `GET /student/dashboard` - Student dashboard
- `GET /student/exam/<id>/take` - Take exam
- `POST /student/exam/<id>/submit` - Submit exam answers

### AI Grading
- `POST /api/grade` - Grade single answer
- `POST /api/grade_batch` - Grade multiple answers
- `POST /api/test_grading` - Test grading system

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request


# SmartGrader - AI-Powered Exam Grading

SmartGrader is a web application that makes grading student exams easier and faster. It uses AI to automatically score submissions and provide meaningful feedback. The system works entirely with PDF files, giving both instructors and students a smooth workflow.

## What It Does

- **Automatic Grading**: Each answer is graded by AI with detailed feedback.
- **Handles PDFs**: Upload exam PDFs, and the system extracts questions and evaluates answers.
- **Flexible Exam Setup**: You can create exams manually or let the system process them automatically.
- **Instructor Dashboard**: Manage exams, track submissions, and review results all in one place.
- **Student Dashboard**: See available exams, submit answers, and check scores.

## How to Get Started

### Requirements

- Python 3.8 or higher
- DeepSeek API key
- Internet access

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd SmartGrader
   ```

2. Run the setup script:
   ```bash
   python setup.py
   ```

3. Add your API key and email configuration in a `.env` file:
   ```
   DEEPSEEK_API_KEY=your_deepseek_token_here
   
   # Email Configuration (for password reset functionality)
   SMTP_EMAIL=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```
   
   **Note:** For Gmail, you'll need to use an App Password instead of your regular password. To generate an App Password:
   1. Go to your Google Account settings
   2. Navigate to Security
   3. Enable 2-Step Verification if not already enabled
   4. Generate an App Password for "Mail"
   5. Use this App Password in the SMTP_PASSWORD field

4. Start the application:
   ```bash
   python app.py
   ```

5. Open your browser at `http://localhost:5000` and log in:
   - **Instructor**: teacher / password
   - **Student**: student / password
   - **Admin**: admin / password

## How to Use

### For Instructors

1. Upload a PDF exam or create questions manually.
2. Let the system extract questions or edit them if needed.
3. Monitor student submissions and their status.
4. Grade submissions automatically using AI and review feedback.
5. Re-evaluate any submission if grading criteria change.

### For Students

1. Browse available exams from your dashboard.
2. Submit answers either by typing them or uploading a PDF file.
3. Check your scores and feedback once the exam is graded.

## File Support

- Only PDF files are supported for both exams and student submissions.
- The system extracts text from PDFs while keeping formatting intact.

## Running Tests

To make sure everything is working:

```bash
python test_phi_grading.py
```

## Troubleshooting

- If grading fails, check that your API key is correct and that your system has enough memory.
- Ensure PDFs are properly formatted and not password-protected.
- Reset the database (`site.db`) if you encounter database issues.

## Project Structure

```
SmartGrader/
├── app.py
├── config.py
├── models.py
├── grader/exam_grader.py
├── routes/instructor.py
├── routes/student.py
├── templates/
├── static/
├── models/
├── uploads/
└── requirements.txt
```

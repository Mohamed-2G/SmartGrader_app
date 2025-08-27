SmartGrader - AI-Powered Exam Grading

SmartGrader is a web application that makes grading student exams easier and faster. It uses AI to automatically score submissions and provide meaningful feedback. The system works entirely with PDF files, giving both instructors and students a smooth workflow.

What It Does

Automatic Grading: Each answer is graded by AI with detailed feedback.

Handles PDFs: Upload exam PDFs, and the system extracts questions and evaluates answers.

Flexible Exam Setup: You can create exams manually or let the system process them automatically.

Instructor Dashboard: Manage exams, track submissions, and review results all in one place.

Student Dashboard: See available exams, submit answers, and check scores.

How to Get Started
Requirements

Python 3.8 or higher

DeepSeek API key

Internet access

Installation

Clone the repository:

git clone <repository-url>
cd SmartGrader


Run the setup script:

python setup.py


Add your API key in a .env file:

DEEPSEEK_API_KEY=your_deepseek_token_here


Start the application:

python app.py


Open your browser at http://localhost:5000 and log in:

Instructor: teacher / password

Student: student / password

Admin: admin / password

How to Use
For Instructors

Upload a PDF exam or create questions manually.

Let the system extract questions or edit them if needed.

Monitor student submissions and their status.

Grade submissions automatically using AI and review feedback.

Re-evaluate any submission if grading criteria change.

For Students

Browse available exams from your dashboard.

Submit answers either by typing them or uploading a PDF file.

Check your scores and feedback once the exam is graded.

File Support

Only PDF files are supported for both exams and student submissions.

The system extracts text from PDFs while keeping formatting intact.

Running Tests

To make sure everything is working:

python test_phi_grading.py
python -m pytest tests/

Troubleshooting

If grading fails, check that your API key is correct and that your system has enough memory.

Ensure PDFs are properly formatted and not password-protected.

Reset the database (site.db) if you encounter database issues.

Project Structure
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

Contributing

Fork the project.

Create a branch for your feature.

Make your changes and add tests.

Submit a pull request.

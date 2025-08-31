import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('GMAIL_USER')
    MAIL_PASSWORD = os.getenv('GMAIL_PASS')
    
    # Email Configuration for Password Reset
    SMTP_EMAIL = os.getenv('SMTP_EMAIL', 'noreply@smartgrader.com')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    
    # File upload settings
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

# Export variables at module level for direct import
ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS
OPENAI_API_KEY = Config.OPENAI_API_KEY
DEEPSEEK_API_KEY = Config.DEEPSEEK_API_KEY
SMTP_EMAIL = Config.SMTP_EMAIL
SMTP_PASSWORD = Config.SMTP_PASSWORD
SMTP_SERVER = Config.SMTP_SERVER
SMTP_PORT = Config.SMTP_PORT

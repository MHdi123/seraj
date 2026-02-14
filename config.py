import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'seraj-quran-university-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///seraj.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # تنظیمات آپلود
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # تنظیمات ایمیل (برای توسعه آینده)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # تنظیمات اپلیکیشن
    APP_NAME = 'سِراج - پلتفرم مدیریت فعالیت‌های قرآنی'
    POSTS_PER_PAGE = 10
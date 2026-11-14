"""
config.py
Central application configuration loaded from environment variables (.env).
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_insecure_key_change_in_production')
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Prevents unexpected form expiry during demo
    
    # MySQL Database Connection
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'smart_campus')
    
    # Debug mode
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    # File Uploads (Resolution Evidence - PRD Section 15)
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


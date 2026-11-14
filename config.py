"""
config.py
Central application configuration loaded from environment variables (.env).
"""

import os
import secrets
import logging
from dotenv import load_dotenv

load_dotenv()

# Detect environment
FLASK_ENV = os.getenv('FLASK_ENV', 'development').lower()


class Config:
    # Flask Security
    # Fail safely in production if SECRET_KEY is omitted; generate secure random key in dev
    _raw_secret = os.getenv('SECRET_KEY')
    if not _raw_secret:
        if FLASK_ENV == 'production':
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "SECRET_KEY environment variable is missing in production. Application will not start."
            )
        logging.warning("No SECRET_KEY set in environment. Generating an ephemeral cryptographic key for development.")
        SECRET_KEY = secrets.token_hex(32)
    else:
        SECRET_KEY = _raw_secret
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Prevents unexpected form expiry during demo
    
    # MySQL Database Connection
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'smart_campus')
    
    # Debug mode - strictly disabled by default; only active if explicitly set to true
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    # File Uploads (Resolution Evidence)
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    ALLOWED_MIME_TYPES = {'image/png', 'image/jpeg', 'image/webp'}


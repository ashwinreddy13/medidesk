import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def _resolve_database_path():
    if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        return os.environ.get('DATABASE_PATH', '/tmp/medidesk.db')
    env_path = os.environ.get('DATABASE_PATH')
    if env_path:
        return env_path
    default_dir = os.path.join(BASE_DIR, 'database')
    try:
        os.makedirs(default_dir, exist_ok=True)
        test_file = os.path.join(default_dir, '.write_test')
        with open(test_file, 'w') as f:
            f.write('')
        os.remove(test_file)
        return os.path.join(default_dir, 'medidesk.db')
    except (OSError, PermissionError):
        return '/tmp/medidesk.db'

class Config:
    """Base application configuration with security defaults."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'medidesk-dev-secret-key-change-in-production-2026-vbit')
    DATABASE_PATH = _resolve_database_path()
    
    # Session Security
    SESSION_COOKIE_NAME = 'medidesk_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    
    # Rate Limiting & Throttling
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_SECONDS = 300  # 5 minutes
    
    # Application Mode
    DEMO_MODE = True
    SYNTHETIC_DATA_BANNER = "Demo Environment — Synthetic Data Only. Not for clinical diagnosis."


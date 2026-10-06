import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, request
from database.db import get_db
from security.audit import log_audit_event, get_client_ip

def hash_password(password):
    """Hash password using pbkdf2:sha256 with strong salt."""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(stored_hash, password):
    """Verify password against hashed string."""
    if not stored_hash or not password:
        return False
    return check_password_hash(stored_hash, password)

def is_login_throttled(identifier, ip_address=None):
    """
    Check if account or IP is temporarily locked due to repeated failed logins.
    Threshold: 5 failed attempts in the last 5 minutes (300 seconds).
    """
    if not ip_address:
        ip_address = get_client_ip()

    conn = get_db()
    cursor = conn.cursor()
    five_min_ago = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        SELECT COUNT(*) as failed_count
        FROM login_attempts
        WHERE (identifier = ? OR ip_address = ?)
          AND success = 0
          AND attempt_time >= ?
    ''', (identifier.strip().lower(), ip_address, five_min_ago))

    count = cursor.fetchone()['failed_count']
    conn.close()

    return count >= 5

def record_login_attempt(identifier, success, ip_address=None):
    """Record an authentication outcome for rate limiting and threat detection."""
    if not ip_address:
        ip_address = get_client_ip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO login_attempts (identifier, ip_address, success)
        VALUES (?, ?, ?)
    ''', (identifier.strip().lower(), ip_address, 1 if success else 0))
    conn.commit()
    conn.close()

def login_user(user):
    """
    Regenerate session to prevent session fixation attacks,
    populate user session payload, and initialize CSRF token.
    """
    # Clear any previous session data
    session.clear()
    
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['user_role'] = user['role']
    session['user_specialty'] = user['specialty'] if 'specialty' in user.keys() else None
    session['csrf_token'] = secrets.token_hex(32)
    session.permanent = True

    # Audit login success
    log_audit_event(
        user_id=user['id'],
        action="LOGIN_SUCCESS",
        resource_type="AUTH",
        resource_id=str(user['id']),
        result="Allowed",
        details=f"User {user['role']} logged in"
    )

def logout_user():
    """Clear session data and log audit record."""
    user_id = session.get('user_id')
    user_role = session.get('user_role')

    if user_id:
        log_audit_event(
            user_id=user_id,
            action="LOGOUT",
            resource_type="AUTH",
            resource_id=str(user_id),
            result="Allowed",
            details=f"User {user_role} logged out"
        )
    session.clear()


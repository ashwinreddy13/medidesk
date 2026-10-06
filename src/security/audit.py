import hashlib
from flask import request
from database.db import get_db

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def get_client_ip():
    """Retrieve client IP address safely from request headers."""
    if request:
        if request.headers.getlist("X-Forwarded-For"):
            return request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        return request.remote_addr or "127.0.0.1"
    return "127.0.0.1"

def log_audit_event(user_id, action, resource_type, resource_id, result, details=None, ip_address=None):
    """
    Append an immutable, privacy-conscious audit log with cryptographic SHA-256 hash chaining.
    Never logs passwords, tokens, or plaintext medical contents.
    """
    conn = get_db()
    cursor = conn.cursor()

    if not ip_address:
        ip_address = get_client_ip()

    # Retrieve latest hash
    cursor.execute("SELECT current_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
    last_row = cursor.fetchone()
    prev_hash = last_row['current_hash'] if last_row and last_row['current_hash'] else GENESIS_HASH

    # Clean details to ensure zero secrets leakage
    clean_details = str(details or "")[:255]
    for sensitive_word in ['password', 'secret', 'token', 'key', 'hash']:
        if sensitive_word in clean_details.lower():
            clean_details = "[REDACTED_SECURITY_DATA]"

    # Calculate SHA-256 chained hash
    payload = f"{prev_hash}:{user_id}:{action}:{resource_type}:{resource_id}:{result}:{clean_details}"
    current_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

    cursor.execute('''
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address, result, details, prev_hash, current_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, action, resource_type, str(resource_id or ""), ip_address, result, clean_details, prev_hash, current_hash))

    conn.commit()
    conn.close()

def verify_audit_log_integrity():
    """
    Cryptographically verify the tamper-evident hash chain across all audit logs.
    Returns: (is_valid: bool, broken_id: int or None, total_verified: int)
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    expected_prev = GENESIS_HASH
    for row in rows:
        if row['prev_hash'] != expected_prev:
            return False, row['id'], len(rows)
        
        # Recalculate hash
        payload = f"{row['prev_hash']}:{row['user_id']}:{row['action']}:{row['resource_type']}:{row['resource_id']}:{row['result']}:{row['details']}"
        calculated_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        if calculated_hash != row['current_hash']:
            return False, row['id'], len(rows)
            
        expected_prev = row['current_hash']

    return True, None, len(rows)


from database.db import get_db
from security.auth import hash_password
from security.validation import validate_name, validate_email, validate_password_strength, sanitize_text
from security.audit import log_audit_event

def get_user_by_id(user_id):
    """Retrieve user dictionary by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, phone, specialty, is_active, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    """Retrieve user dictionary by email (including password hash for authentication)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip().lower(),))
    user = cursor.fetchone()
    conn.close()
    return user

def register_patient(name, email, password, phone=None):
    """
    Register a new patient with server-side validation and password hashing.
    Returns: (success: bool, message_or_user_id)
    """
    v_name, err = validate_name(name)
    if not v_name:
        return False, err

    v_email, err = validate_email(email)
    if not v_email:
        return False, err

    v_pw, err = validate_password_strength(password)
    if not v_pw:
        return False, err

    conn = get_db()
    cursor = conn.cursor()

    # Check if email is already taken
    cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (email.strip().lower(),))
    if cursor.fetchone():
        conn.close()
        return False, "An account with this email address already exists."

    pw_hash = hash_password(password)
    clean_phone = sanitize_text(phone, 30) if phone else None

    try:
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone, specialty)
            VALUES (?, ?, ?, 'patient', ?, NULL)
        ''', (name.strip(), email.strip().lower(), pw_hash, clean_phone))
        patient_id = cursor.lastrowid
        conn.commit()

        log_audit_event(
            user_id=patient_id,
            action="PATIENT_REGISTERED",
            resource_type="USER",
            resource_id=str(patient_id),
            result="Allowed",
            details="New patient registered account"
        )
        conn.close()
        return True, patient_id
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, "Registration failed due to a database error."

def update_patient_profile(user_id, name, phone):
    """Update profile information for a patient."""
    v_name, err = validate_name(name)
    if not v_name:
        return False, err

    conn = get_db()
    cursor = conn.cursor()
    clean_phone = sanitize_text(phone, 30) if phone else None

    cursor.execute('''
        UPDATE users
        SET name = ?, phone = ?
        WHERE id = ? AND role = 'patient'
    ''', (name.strip(), clean_phone, user_id))
    conn.commit()
    conn.close()

    log_audit_event(
        user_id=user_id,
        action="PROFILE_UPDATED",
        resource_type="USER",
        resource_id=str(user_id),
        result="Allowed",
        details="Patient updated personal profile"
    )
    return True, "Profile updated successfully."

def get_all_doctors():
    """Retrieve list of all active doctors with specialties and schedules."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, email, specialty, phone
        FROM users
        WHERE role = 'doctor' AND is_active = 1
        ORDER BY name ASC
    ''')
    doctors = cursor.fetchall()
    conn.close()
    return doctors

def get_all_patients():
    """Retrieve all patients for administrative management."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, email, phone, created_at, is_active
        FROM users
        WHERE role = 'patient'
        ORDER BY created_at DESC
    ''')
    patients = cursor.fetchall()
    conn.close()
    return patients


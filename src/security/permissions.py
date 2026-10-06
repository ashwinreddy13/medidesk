from functools import wraps
from flask import session, redirect, url_for, flash, abort, request, render_template
from security.audit import log_audit_event
from database.db import get_db

def login_required(f):
    """Ensure user is logged in, else redirect to login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if API request expecting JSON
            if request.path.startswith('/api/') or request.is_json:
                return {"error": "Authentication required. Please log in."}, 401
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*allowed_roles):
    """
    Centralized role-based access control (RBAC).
    Rejects unauthorized roles with HTTP 403 and records an audit log.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/') or request.is_json:
                    return {"error": "Authentication required."}, 401
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.path))

            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                # Log security alert
                log_audit_event(
                    user_id=session.get('user_id'),
                    action="UNAUTHORIZED_ACCESS_ATTEMPT",
                    resource_type="ENDPOINT",
                    resource_id=request.path,
                    result="Denied",
                    details=f"Role '{user_role}' denied access to {request.path}. Allowed roles: {allowed_roles}"
                )
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def verify_patient_appointment_ownership(appointment_id, patient_id):
    """
    Anti-IDOR validation: Verify that the appointment actually belongs to the patient.
    Returns: appointment row if authorized, else raises/returns 403.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, d.name as doctor_name, d.specialty as doctor_specialty
        FROM appointments a
        JOIN users d ON a.doctor_id = d.id
        WHERE a.id = ?
    ''', (appointment_id,))
    appt = cursor.fetchone()
    conn.close()

    if not appt:
        return None

    if appt['patient_id'] != patient_id:
        log_audit_event(
            user_id=patient_id,
            action="IDOR_ATTEMPT_BLOCKED",
            resource_type="APPOINTMENT",
            resource_id=str(appointment_id),
            result="Denied",
            details=f"Patient {patient_id} attempted unauthorized access to appointment {appointment_id}"
        )
        abort(403)

    return appt

def verify_doctor_appointment_ownership(appointment_id, doctor_id):
    """
    Anti-IDOR validation: Verify that the appointment is assigned to the requesting doctor.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, p.name as patient_name, p.email as patient_email, p.phone as patient_phone
        FROM appointments a
        JOIN users p ON a.patient_id = p.id
        WHERE a.id = ?
    ''', (appointment_id,))
    appt = cursor.fetchone()
    conn.close()

    if not appt:
        return None

    if appt['doctor_id'] != doctor_id:
        log_audit_event(
            user_id=doctor_id,
            action="IDOR_ATTEMPT_BLOCKED",
            resource_type="APPOINTMENT",
            resource_id=str(appointment_id),
            result="Denied",
            details=f"Doctor {doctor_id} attempted unauthorized access to appointment {appointment_id}"
        )
        abort(403)

    return appt

def verify_patient_record_access(record_id, user_id, user_role):
    """
    Anti-IDOR & Healthcare Access Control:
    - Patient can only access their own record.
    - Doctor can only access record if they authored it OR have an active/completed appointment relationship with the patient.
    - Admin has no clinical access to individual patient records (least privilege).
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, p.name as patient_name, d.name as doctor_name, d.specialty as doctor_specialty
        FROM medical_records r
        JOIN users p ON r.patient_id = p.id
        JOIN users d ON r.doctor_id = d.id
        WHERE r.id = ?
    ''', (record_id,))
    record = cursor.fetchone()

    if not record:
        conn.close()
        return None

    if user_role == 'patient':
        if record['patient_id'] != user_id:
            conn.close()
            log_audit_event(
                user_id=user_id,
                action="IDOR_ATTEMPT_BLOCKED",
                resource_type="MEDICAL_RECORD",
                resource_id=str(record_id),
                result="Denied",
                details=f"Patient {user_id} attempted unauthorized view of record {record_id}"
            )
            abort(403)
    elif user_role == 'doctor':
        # Check if this doctor is either the author or has an appointment with this patient
        if record['doctor_id'] != user_id:
            cursor.execute('''
                SELECT COUNT(*) as count FROM appointments
                WHERE doctor_id = ? AND patient_id = ?
            ''', (user_id, record['patient_id']))
            relation = cursor.fetchone()['count']
            if relation == 0:
                conn.close()
                log_audit_event(
                    user_id=user_id,
                    action="UNAUTHORIZED_RECORD_ACCESS",
                    resource_type="MEDICAL_RECORD",
                    resource_id=str(record_id),
                    result="Denied",
                    details=f"Doctor {user_id} lacks care relationship with patient {record['patient_id']}"
                )
                abort(403)
    else:
        conn.close()
        # Admin does not have direct access to individual EHRs
        abort(403)

    conn.close()
    return record


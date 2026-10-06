import sqlite3
from datetime import datetime
from database.db import get_db
from services.scheduling import generate_available_slots
from security.validation import validate_appointment_date, validate_appointment_time, sanitize_text
from security.audit import log_audit_event

VALID_TRANSITIONS = {
    'Pending': ['Confirmed', 'Cancelled'],
    'Confirmed': ['Completed', 'Cancelled'],
    'Completed': [],
    'Cancelled': []
}

def create_appointment(patient_id, doctor_id, date_str, time_str, reason):
    """
    Independently validate and create an appointment in 'Pending' status.
    Uses atomic SQLite transactions and partial unique indexing to prevent race condition double-bookings.
    """
    clean_reason = sanitize_text(reason, 250)
    if not clean_reason or len(clean_reason) < 3:
        return False, "Please provide a brief reason for consultation (minimum 3 characters)."

    # 1. Server-side validation of doctor, date, and availability
    valid, err, available_slots = generate_available_slots(doctor_id, date_str)
    if not valid:
        return False, err

    if time_str not in available_slots:
        return False, f"The selected time slot ({time_str}) is not available. Please choose another slot."

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        ''', (patient_id, doctor_id, date_str, time_str, clean_reason))
        appt_id = cursor.lastrowid
        conn.commit()

        log_audit_event(
            user_id=patient_id,
            action="APPOINTMENT_CREATED",
            resource_type="APPOINTMENT",
            resource_id=str(appt_id),
            result="Allowed",
            details=f"Booked slot with Doctor {doctor_id} on {date_str} at {time_str}"
        )
        conn.close()
        return True, appt_id
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return False, "This time slot was just booked by another patient. Please select another slot."
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, "Failed to book appointment due to an internal system error."

def transition_appointment_status(appointment_id, new_status, actor_user_id, actor_role):
    """
    Enforce strict state machine transitions:
    - Pending -> Confirmed (Doctor only)
    - Pending -> Cancelled (Patient or Doctor)
    - Confirmed -> Completed (Doctor only)
    - Confirmed -> Cancelled (Patient or Doctor)
    - Completed -> any: BLOCKED
    - Cancelled -> any: BLOCKED
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    appt = cursor.fetchone()

    if not appt:
        conn.close()
        return False, "Appointment not found."

    current_status = appt['status']

    # 1. State machine validation
    allowed_next = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed_next:
        conn.close()
        log_audit_event(
            user_id=actor_user_id,
            action="INVALID_STATE_TRANSITION",
            resource_type="APPOINTMENT",
            resource_id=str(appointment_id),
            result="Denied",
            details=f"Attempted invalid transition from {current_status} to {new_status}"
        )
        return False, f"Invalid transition: Cannot change status from '{current_status}' to '{new_status}'."

    # 2. Role permission check
    if new_status == 'Confirmed' and actor_role != 'doctor':
        conn.close()
        return False, "Only authorized doctors can confirm appointment requests."

    if new_status == 'Completed' and actor_role != 'doctor':
        conn.close()
        return False, "Only attending doctors can mark appointments as completed."

    # 3. Ownership check
    if actor_role == 'patient' and appt['patient_id'] != actor_user_id:
        conn.close()
        return False, "You can only cancel your own appointments."
        
    if actor_role == 'doctor' and appt['doctor_id'] != actor_user_id:
        conn.close()
        return False, "You can only manage appointments assigned to you."

    cursor.execute('''
        UPDATE appointments
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, appointment_id))
    conn.commit()

    action_map = {
        'Confirmed': "APPOINTMENT_CONFIRMED",
        'Cancelled': "APPOINTMENT_CANCELLED",
        'Completed': "APPOINTMENT_COMPLETED"
    }

    log_audit_event(
        user_id=actor_user_id,
        action=action_map.get(new_status, "APPOINTMENT_UPDATED"),
        resource_type="APPOINTMENT",
        resource_id=str(appointment_id),
        result="Allowed",
        details=f"Status transitioned from {current_status} to {new_status} by {actor_role}"
    )

    conn.close()
    return True, f"Appointment status successfully updated to {new_status}."

def get_patient_appointments(patient_id):
    """Retrieve all appointments for a patient sorted by date and time."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, d.name as doctor_name, d.specialty as doctor_specialty, d.email as doctor_email
        FROM appointments a
        JOIN users d ON a.doctor_id = d.id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (patient_id,))
    appointments = cursor.fetchall()
    conn.close()
    return appointments

def get_doctor_appointments(doctor_id, status_filter=None, date_filter=None):
    """Retrieve appointments for a doctor with optional filters."""
    conn = get_db()
    cursor = conn.cursor()

    query = '''
        SELECT a.*, p.name as patient_name, p.email as patient_email, p.phone as patient_phone
        FROM appointments a
        JOIN users p ON a.patient_id = p.id
        WHERE a.doctor_id = ?
    '''
    params = [doctor_id]

    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)

    if date_filter:
        query += " AND a.appointment_date = ?"
        params.append(date_filter)

    query += " ORDER BY a.appointment_date ASC, a.appointment_time ASC"

    cursor.execute(query, tuple(params))
    appts = cursor.fetchall()
    conn.close()
    return appts

def get_all_appointments_admin():
    """Retrieve system-wide appointment overview for admin dashboard."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, p.name as patient_name, d.name as doctor_name, d.specialty as doctor_specialty
        FROM appointments a
        JOIN users p ON a.patient_id = p.id
        JOIN users d ON a.doctor_id = d.id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        LIMIT 100
    ''')
    appts = cursor.fetchall()
    conn.close()
    return appts


import hashlib
from datetime import date
from database.db import get_db
from security.validation import sanitize_text
from security.audit import log_audit_event

def create_medical_record(patient_id, doctor_id, appointment_id, diagnosis, prescription, notes=""):
    """
    Create a new synthetic medical record authored by an authorized doctor.
    Computes a cryptographic SHA-256 hash to ensure medical record integrity.
    """
    clean_diag = sanitize_text(diagnosis, 300)
    clean_rx = sanitize_text(prescription, 500)
    clean_notes = sanitize_text(notes, 1000)

    if not clean_diag or len(clean_diag) < 3:
        return False, "Please enter a valid diagnosis (minimum 3 characters)."
    if not clean_rx or len(clean_rx) < 2:
        return False, "Please enter prescription or treatment advice."

    today_str = date.today().strftime("%Y-%m-%d")

    # Generate tamper-evident record hash
    payload = f"{patient_id}:{doctor_id}:{appointment_id}:{today_str}:{clean_diag}:{clean_rx}"
    record_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO medical_records (patient_id, doctor_id, appointment_id, diagnosis, prescription, notes, record_date, record_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patient_id, doctor_id, appointment_id, clean_diag, clean_rx, clean_notes, today_str, record_hash))
        record_id = cursor.lastrowid

        # Mark appointment completed if linked
        if appointment_id:
            cursor.execute("UPDATE appointments SET status = 'Completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (appointment_id,))

        conn.commit()

        log_audit_event(
            user_id=doctor_id,
            action="MEDICAL_RECORD_CREATED",
            resource_type="MEDICAL_RECORD",
            resource_id=str(record_id),
            result="Allowed",
            details=f"Doctor {doctor_id} created medical record for patient {patient_id}"
        )
        conn.close()
        return True, record_id
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, "Failed to store medical record."

def get_patient_records(patient_id):
    """Retrieve all synthetic medical records for a patient."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, d.name as doctor_name, d.specialty as doctor_specialty, d.email as doctor_email
        FROM medical_records r
        JOIN users d ON r.doctor_id = d.id
        WHERE r.patient_id = ?
        ORDER BY r.record_date DESC, r.id DESC
    ''', (patient_id,))
    records = cursor.fetchall()
    conn.close()
    return records

def get_patient_timeline(patient_id):
    """
    Generate unified chronological Patient Health Timeline.
    Combines appointments and medical records sorted descending by date.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Completed appointments
    cursor.execute('''
        SELECT a.id, 'appointment' as type, a.appointment_date as event_date, a.appointment_time as event_time,
               a.reason as title, a.status as status, d.name as doctor_name, d.specialty as doctor_specialty,
               NULL as prescription, NULL as notes, NULL as record_hash
        FROM appointments a
        JOIN users d ON a.doctor_id = d.id
        WHERE a.patient_id = ? AND a.status = 'Completed'
    ''', (patient_id,))
    appts = cursor.fetchall()

    # Medical records
    cursor.execute('''
        SELECT r.id, 'record' as type, r.record_date as event_date, '12:00' as event_time,
               r.diagnosis as title, 'Verified EHR' as status, d.name as doctor_name, d.specialty as doctor_specialty,
               r.prescription, r.notes, r.record_hash
        FROM medical_records r
        JOIN users d ON r.doctor_id = d.id
        WHERE r.patient_id = ?
    ''', (patient_id,))
    recs = cursor.fetchall()
    conn.close()

    timeline = []
    for a in appts:
        timeline.append(dict(a))
    for r in recs:
        timeline.append(dict(r))

    # Sort descending by date and time
    timeline.sort(key=lambda x: (x['event_date'], x['event_time']), reverse=True)
    return timeline


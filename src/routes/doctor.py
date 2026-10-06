from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from datetime import date
from security.permissions import login_required, roles_required, verify_doctor_appointment_ownership
from services.users import get_user_by_id
from services.appointments import get_doctor_appointments, transition_appointment_status
from services.medical_records import create_medical_record, get_patient_records
from database.db import get_db

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/dashboard')
@login_required
@roles_required('doctor')
def dashboard():
    """Doctor overview dashboard with appointment metrics and queues."""
    doctor_id = session['user_id']
    user = get_user_by_id(doctor_id)
    all_appts = get_doctor_appointments(doctor_id)

    today_str = date.today().strftime("%Y-%m-%d")
    today_appts = [a for a in all_appts if a['appointment_date'] == today_str]
    pending_appts = [a for a in all_appts if a['status'] == 'Pending']
    confirmed_appts = [a for a in all_appts if a['status'] == 'Confirmed']
    completed_appts = [a for a in all_appts if a['status'] == 'Completed']

    # Unique patients treated by this doctor
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT p.id, p.name, p.email, p.phone,
               MAX(a.appointment_date) as last_visit,
               COUNT(a.id) as total_appointments
        FROM appointments a
        JOIN users p ON a.patient_id = p.id
        WHERE a.doctor_id = ?
        GROUP BY p.id
        ORDER BY last_visit DESC
    ''', (doctor_id,))
    relevant_patients = cursor.fetchall()
    conn.close()

    return render_template(
        'doctor/dashboard.html',
        user=user,
        today_appts=today_appts,
        pending_appts=pending_appts,
        confirmed_appts=confirmed_appts,
        completed_appts=completed_appts,
        relevant_patients=relevant_patients,
        total_count=len(all_appts)
    )

@doctor_bp.route('/appointments')
@login_required
@roles_required('doctor')
def appointments():
    """List of all appointments assigned to the doctor with filter options."""
    doctor_id = session['user_id']
    status_filter = request.args.get('status')
    date_filter = request.args.get('date')

    appts = get_doctor_appointments(doctor_id, status_filter=status_filter, date_filter=date_filter)
    return render_template('doctor/appointments.html', appointments=appts, current_status=status_filter)

@doctor_bp.route('/appointments/<int:appointment_id>/confirm', methods=['POST'])
@login_required
@roles_required('doctor')
def confirm_appointment(appointment_id):
    """Confirm a pending appointment with Anti-IDOR ownership verification."""
    doctor_id = session['user_id']
    appt = verify_doctor_appointment_ownership(appointment_id, doctor_id)
    if not appt:
        flash("Appointment not found or not assigned to you.", "danger")
        return redirect(url_for('doctor.appointments'))

    success, msg = transition_appointment_status(appointment_id, 'Confirmed', doctor_id, 'doctor')
    if success:
        flash("Appointment confirmed successfully!", "success")
    else:
        flash(msg, "danger")

    return redirect(url_for('doctor.appointments'))

@doctor_bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@roles_required('doctor')
def cancel_appointment(appointment_id):
    """Cancel an appointment assigned to this doctor."""
    doctor_id = session['user_id']
    appt = verify_doctor_appointment_ownership(appointment_id, doctor_id)
    if not appt:
        flash("Appointment not found or unauthorized.", "danger")
        return redirect(url_for('doctor.appointments'))

    success, msg = transition_appointment_status(appointment_id, 'Cancelled', doctor_id, 'doctor')
    if success:
        flash("Appointment has been cancelled.", "info")
    else:
        flash(msg, "danger")

    return redirect(url_for('doctor.appointments'))

@doctor_bp.route('/appointments/<int:appointment_id>/complete', methods=['POST'])
@login_required
@roles_required('doctor')
def complete_appointment(appointment_id):
    """Directly mark appointment completed or redirect to add medical record."""
    doctor_id = session['user_id']
    appt = verify_doctor_appointment_ownership(appointment_id, doctor_id)
    if not appt:
        flash("Appointment not found or unauthorized.", "danger")
        return redirect(url_for('doctor.appointments'))

    return redirect(url_for('doctor.add_medical_record', patient_id=appt['patient_id'], appointment_id=appointment_id))

@doctor_bp.route('/patients/<int:patient_id>')
@login_required
@roles_required('doctor')
def patient_view(patient_id):
    """
    Authorized Patient Information:
    Doctor can ONLY view information of patients who have an appointment with this doctor!
    """
    doctor_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    # Check relation
    cursor.execute('''
        SELECT COUNT(*) as count FROM appointments
        WHERE doctor_id = ? AND patient_id = ?
    ''', (doctor_id, patient_id))
    has_relationship = cursor.fetchone()['count'] > 0

    if not has_relationship:
        conn.close()
        flash("Access Denied: You do not have an active or historical clinical relationship with this patient.", "danger")
        abort(403)

    patient = get_user_by_id(patient_id)
    records = get_patient_records(patient_id)

    cursor.execute('''
        SELECT a.*, d.name as doctor_name
        FROM appointments a
        JOIN users d ON a.doctor_id = d.id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC
    ''', (patient_id,))
    patient_appts = cursor.fetchall()
    conn.close()

    return render_template('doctor/patient_view.html', patient=patient, records=records, appointments=patient_appts)

@doctor_bp.route('/records/add/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@roles_required('doctor')
def add_medical_record(patient_id):
    """Add a synthetic medical record for an authorized patient."""
    doctor_id = session['user_id']
    appointment_id = request.args.get('appointment_id', type=int)

    # Verify doctor-patient care relationship
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM appointments WHERE doctor_id = ? AND patient_id = ?", (doctor_id, patient_id))
    if cursor.fetchone()['count'] == 0:
        conn.close()
        flash("Access Denied: No clinical relationship with this patient.", "danger")
        abort(403)
    conn.close()

    patient = get_user_by_id(patient_id)

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis', '')
        prescription = request.form.get('prescription', '')
        notes = request.form.get('notes', '')
        form_appt_id = request.form.get('appointment_id', type=int) or appointment_id

        success, result = create_medical_record(patient_id, doctor_id, form_appt_id, diagnosis, prescription, notes)
        if not success:
            flash(result, "danger")
            return render_template('doctor/add_record.html', patient=patient, appointment_id=form_appt_id, diagnosis=diagnosis, prescription=prescription, notes=notes)

        flash("Medical record successfully authored and cryptographically hashed! The appointment has been completed.", "success")
        return redirect(url_for('doctor.patient_view', patient_id=patient_id))

    return render_template('doctor/add_record.html', patient=patient, appointment_id=appointment_id)


from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from security.permissions import login_required, roles_required, verify_patient_appointment_ownership, verify_patient_record_access
from services.users import get_user_by_id, get_all_doctors, update_patient_profile
from services.appointments import create_appointment, get_patient_appointments, transition_appointment_status
from services.scheduling import generate_available_slots, find_smart_slots
from services.medical_records import get_patient_records, get_patient_timeline
from database.db import get_db

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

@patient_bp.route('/dashboard')
@login_required
@roles_required('patient')
def dashboard():
    """Patient overview dashboard."""
    patient_id = session['user_id']
    user = get_user_by_id(patient_id)
    appts = get_patient_appointments(patient_id)

    # Next upcoming confirmed/pending appointment
    upcoming = [a for a in appts if a['status'] in ('Pending', 'Confirmed')]
    next_appt = upcoming[0] if upcoming else None

    # Summary counts
    total_appts = len(appts)
    completed_count = len([a for a in appts if a['status'] == 'Completed'])
    records = get_patient_records(patient_id)

    return render_template(
        'patient/dashboard.html',
        user=user,
        next_appt=next_appt,
        total_appts=total_appts,
        completed_count=completed_count,
        records_count=len(records),
        recent_appts=appts[:5]
    )

@patient_bp.route('/book', methods=['GET', 'POST'])
@login_required
@roles_required('patient')
def book_appointment():
    """Flow: Select Doctor -> Select Date -> Check Schedule -> Available Slots -> Book."""
    patient_id = session['user_id']
    doctors = get_all_doctors()
    current_date = date.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        date_str = request.form.get('appointment_date')
        time_str = request.form.get('appointment_time')
        reason = request.form.get('reason', '')

        try:
            doc_int = int(doctor_id)
        except (ValueError, TypeError):
            flash("Invalid doctor selection. Please choose a specialist from the list.", "danger")
            return redirect(url_for('patient.book_appointment'))

        if not time_str or not time_str.strip():
            flash("Please click on one of the available time slots below before submitting.", "danger")
            return render_template('patient/book.html', doctors=doctors, selected_doc=doc_int, selected_date=date_str, reason=reason, current_date=current_date)

        success, result = create_appointment(patient_id, doc_int, date_str, time_str, reason)
        if not success:
            flash(result, "danger")
            return render_template('patient/book.html', doctors=doctors, selected_doc=doc_int, selected_date=date_str, reason=reason, current_date=current_date)

        flash("Appointment request submitted successfully! Your booking is currently Pending doctor confirmation.", "success")
        return redirect(url_for('patient.my_appointments'))

    # Pre-select doctor if passed via query string
    pre_doc = request.args.get('doctor_id', type=int)
    pre_date = request.args.get('date', current_date)
    pre_time = request.args.get('time', '')
    pre_reason = request.args.get('reason', '')

    return render_template('patient/book.html', doctors=doctors, pre_doc=pre_doc, pre_date=pre_date, pre_time=pre_time, pre_reason=pre_reason, current_date=current_date)

@patient_bp.route('/api/slots')
@login_required
@roles_required('patient')
def get_slots_api():
    """
    Independent server-side slot check for dynamic frontend slot picker.
    GET /patient/api/slots?doctor_id=X&date=YYYY-MM-DD
    """
    doctor_id = request.args.get('doctor_id', type=int)
    date_str = request.args.get('date', type=str)

    if not doctor_id or not date_str:
        return jsonify({'success': False, 'error': 'doctor_id and date query parameters are required.', 'slots': []}), 400

    valid, err, slots = generate_available_slots(doctor_id, date_str)
    if not valid:
        return jsonify({'success': False, 'error': err, 'slots': []}), 400

    return jsonify({'success': True, 'slots': slots})

@patient_bp.route('/best-slot', methods=['GET', 'POST'])
@login_required
@roles_required('patient')
def best_slot():
    """Smart Appointment Finder: deterministic slot recommendation."""
    specialty = request.args.get('specialty', 'General Consultation')
    timeframe = request.args.get('timeframe', 'this_week')
    time_of_day = request.args.get('time_of_day', 'morning')

    matches = find_smart_slots(specialty=specialty, timeframe=timeframe, time_of_day=time_of_day)

    return render_template(
        'patient/best_slot.html',
        matches=matches,
        current_specialty=specialty,
        current_timeframe=timeframe,
        current_time_of_day=time_of_day
    )

@patient_bp.route('/appointments')
@login_required
@roles_required('patient')
def my_appointments():
    """View appointment history with status indicators."""
    patient_id = session['user_id']
    appts = get_patient_appointments(patient_id)
    return render_template('patient/appointments.html', appointments=appts)

@patient_bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@roles_required('patient')
def cancel_appointment(appointment_id):
    """Cancel appointment with server-side Anti-IDOR ownership check."""
    patient_id = session['user_id']
    appt = verify_patient_appointment_ownership(appointment_id, patient_id)
    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for('patient.my_appointments'))

    success, msg = transition_appointment_status(appointment_id, 'Cancelled', patient_id, 'patient')
    if success:
        flash("Appointment has been successfully cancelled.", "success")
    else:
        flash(msg, "danger")

    return redirect(url_for('patient.my_appointments'))

@patient_bp.route('/records')
@login_required
@roles_required('patient')
def records():
    """View patient's synthetic medical records."""
    patient_id = session['user_id']
    recs = get_patient_records(patient_id)
    return render_template('patient/records.html', records=recs)

@patient_bp.route('/records/<int:record_id>')
@login_required
@roles_required('patient')
def view_record(record_id):
    """View a single medical record with Anti-IDOR enforcement."""
    record = verify_patient_record_access(record_id, session['user_id'], session['user_role'])
    if not record:
        flash("Medical record not found.", "danger")
        return redirect(url_for('patient.records'))
    return render_template('patient/record_detail.html', record=record)

@patient_bp.route('/timeline')
@login_required
@roles_required('patient')
def health_timeline():
    """Visual chronological Patient Health Timeline."""
    patient_id = session['user_id']
    timeline = get_patient_timeline(patient_id)
    return render_template('patient/timeline.html', timeline=timeline)

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@roles_required('patient')
def profile():
    """View and update profile information."""
    patient_id = session['user_id']
    if request.method == 'POST':
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        success, msg = update_patient_profile(patient_id, name, phone)
        if success:
            session['user_name'] = name.strip()
            flash("Profile updated successfully.", "success")
        else:
            flash(msg, "danger")

    user = get_user_by_id(patient_id)
    return render_template('patient/profile.html', user=user)


from datetime import datetime, date, timedelta, time
from database.db import get_db
from security.validation import validate_appointment_date, validate_appointment_time

def get_doctor_schedules(doctor_id):
    """Retrieve all configured active schedule rules for a doctor."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT day_of_week, start_time, end_time, slot_duration
        FROM doctor_schedules
        WHERE doctor_id = ?
        ORDER BY CASE day_of_week
            WHEN 'Monday' THEN 1
            WHEN 'Tuesday' THEN 2
            WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4
            WHEN 'Friday' THEN 5
            WHEN 'Saturday' THEN 6
            WHEN 'Sunday' THEN 7
        END
    ''', (doctor_id,))
    schedules = cursor.fetchall()
    conn.close()
    return schedules

def generate_available_slots(doctor_id, date_str):
    """
    Independently calculate available appointment slots on the server:
    1. Validates doctor exists and is active.
    2. Validates date format and confirms date is not in the past.
    3. Finds doctor's working hours for the day of the week.
    4. Generates slot intervals according to slot_duration.
    5. Excludes already booked active appointments (Pending or Confirmed).
    6. Excludes passed times if the appointment date is today.
    Returns: (is_valid: bool, error_message: str or None, slots: list of 'HH:MM' strings)
    """
    # 1. Validate date
    v_date, err_date, appt_date = validate_appointment_date(date_str)
    if not v_date:
        return False, err_date, []

    conn = get_db()
    cursor = conn.cursor()

    # 2. Validate doctor
    cursor.execute("SELECT id, name, is_active FROM users WHERE id = ? AND role = 'doctor'", (doctor_id,))
    doctor = cursor.fetchone()
    if not doctor or not doctor['is_active']:
        conn.close()
        return False, "Selected doctor was not found or is currently inactive.", []

    # 3. Check day of week
    day_name = appt_date.strftime('%A')  # e.g., 'Monday'
    cursor.execute('''
        SELECT start_time, end_time, slot_duration
        FROM doctor_schedules
        WHERE doctor_id = ? AND day_of_week = ?
    ''', (doctor_id, day_name))
    schedule = cursor.fetchone()

    if not schedule:
        conn.close()
        return True, None, []  # Doctor does not work on this day

    # 4. Generate all theoretical slots
    start_dt = datetime.strptime(schedule['start_time'], "%H:%M")
    end_dt = datetime.strptime(schedule['end_time'], "%H:%M")
    duration = timedelta(minutes=schedule['slot_duration'] or 30)

    generated_slots = []
    curr = start_dt
    while curr + duration <= end_dt:
        slot_str = curr.strftime("%H:%M")
        generated_slots.append(slot_str)
        curr += duration

    # 5. Fetch booked active slots for this doctor on this date
    cursor.execute('''
        SELECT appointment_time
        FROM appointments
        WHERE doctor_id = ?
          AND appointment_date = ?
          AND status IN ('Pending', 'Confirmed')
    ''', (doctor_id, date_str))
    booked_rows = cursor.fetchall()
    booked_slots = set(row['appointment_time'] for row in booked_rows)
    conn.close()

    # 6. Filter out booked slots
    available = [s for s in generated_slots if s not in booked_slots]

    # 7. If date is today, filter out times that have already passed
    now = datetime.now()
    if appt_date == date.today():
        current_time_str = now.strftime("%H:%M")
        available = [s for s in available if s > current_time_str]

    return True, None, available

def find_smart_slots(specialty="General Consultation", timeframe="this_week", time_of_day="morning"):
    """
    Deterministic Smart Appointment Finder:
    Matches doctor specialty, timeframe, and preferred time period to surface the top 3 best available slots.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Find matching doctors
    if specialty and specialty != "any":
        cursor.execute('''
            SELECT id, name, specialty
            FROM users
            WHERE role = 'doctor' AND is_active = 1 AND specialty LIKE ?
        ''', (f"%{specialty}%",))
    else:
        cursor.execute('''
            SELECT id, name, specialty
            FROM users
            WHERE role = 'doctor' AND is_active = 1
        ''')
    doctors = cursor.fetchall()
    conn.close()

    if not doctors:
        return []

    # Determine date range to search
    today = date.today()
    if timeframe == "today":
        target_dates = [today]
    elif timeframe == "tomorrow":
        target_dates = [today + timedelta(days=1)]
    elif timeframe == "next_week":
        # Days 7 to 13
        target_dates = [today + timedelta(days=i) for i in range(7, 14)]
    else:  # this_week (next 7 days)
        target_dates = [today + timedelta(days=i) for i in range(0, 7)]

    # Time period bounds
    time_filters = {
        'morning': ("08:00", "12:00"),
        'afternoon': ("12:00", "16:00"),
        'evening': ("16:00", "20:00"),
        'any': ("00:00", "23:59")
    }
    t_min, t_max = time_filters.get(time_of_day.lower(), ("00:00", "23:59"))

    matches = []
    for d in target_dates:
        d_str = d.strftime("%Y-%m-%d")
        for doc in doctors:
            ok, err, slots = generate_available_slots(doc['id'], d_str)
            if not ok or not slots:
                continue
            
            for s in slots:
                if t_min <= s < t_max:
                    is_first = len(matches) == 0
                    matches.append({
                        'doctor_id': doc['id'],
                        'doctor_name': doc['name'],
                        'specialty': doc['specialty'],
                        'date': d_str,
                        'day_name': d.strftime('%A'),
                        'time': s,
                        'formatted_time': datetime.strptime(s, "%H:%M").strftime("%I:%M %p"),
                        'is_best_match': is_first,
                        'badge': "Best Match ✨" if is_first else ("Early Choice" if s < "10:30" else "Recommended")
                    })
                    if len(matches) >= 5:
                        return matches

    return matches


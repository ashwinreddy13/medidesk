import sqlite3
import os
import hashlib
from werkzeug.security import generate_password_hash

def get_db_path():
    """Retrieve database path from environment or default location."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.environ.get('DATABASE_PATH', os.path.join(base_dir, 'database', 'medidesk.db'))

def get_db():
    """Get SQLite database connection with row factory and foreign keys enabled."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database schema and seed with realistic synthetic data."""
    conn = get_db()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('patient', 'doctor', 'admin')),
            phone TEXT,
            specialty TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Doctor Schedules Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctor_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            day_of_week TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            slot_duration INTEGER DEFAULT 30,
            FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(doctor_id, day_of_week)
        )
    ''')

    # Appointments Table (Unique active booking constraint on doctor + date + time)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Confirmed', 'Cancelled', 'Completed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Partial unique index to enforce doctor + date + time uniqueness only for active slots
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_active_appointment
        ON appointments (doctor_id, appointment_date, appointment_time)
        WHERE status IN ('Pending', 'Confirmed')
    ''')

    # Medical Records Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_id INTEGER,
            diagnosis TEXT NOT NULL,
            prescription TEXT NOT NULL,
            notes TEXT,
            record_date TEXT NOT NULL,
            record_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
        )
    ''')

    # Audit Logs Table with SHA-256 hash chaining
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            result TEXT NOT NULL CHECK(result IN ('Allowed', 'Denied')),
            details TEXT,
            prev_hash TEXT,
            current_hash TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # Login Attempts Throttling Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success INTEGER DEFAULT 0
        )
    ''')

    conn.commit()

    # Check if seed data exists
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()['count'] == 0:
        seed_data(conn)

    conn.close()

def seed_data(conn):
    """Seed synthetic demographic and clinical data."""
    cursor = conn.cursor()

    # Default Passwords
    admin_pw = generate_password_hash("Admin@Secure2026!")
    doctor_pw = generate_password_hash("Doctor@Secure2026!")
    patient_pw = generate_password_hash("Patient@Secure2026!")

    # 1. Admin
    cursor.execute('''
        INSERT INTO users (name, email, password_hash, role, phone, specialty)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ("System Administrator", "admin@medidesk.com", admin_pw, "admin", "+1-555-0100", "Hospital Administration"))

    # 2. Doctors
    doctors = [
        ("Dr. Emily Stone", "doctor@medidesk.com", doctor_pw, "doctor", "+1-555-0101", "Cardiology"),
        ("Dr. Alex Demo", "dr.demo@medidesk.com", doctor_pw, "doctor", "+1-555-0102", "General Consultation"),
        ("Dr. Sarah Chen", "dr.sarah@medidesk.com", doctor_pw, "doctor", "+1-555-0103", "Neurology"),
        ("Dr. Marcus Vance", "dr.marcus@medidesk.com", doctor_pw, "doctor", "+1-555-0104", "Pediatrics")
    ]
    for d in doctors:
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone, specialty)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', d)

    # 3. Patients (Synthetic only)
    patients = [
        ("Alex Johnson", "patient@example.com", patient_pw, "patient", "+1-555-0201", None),
        ("Bob Miller", "patient2@example.com", patient_pw, "patient", "+1-555-0202", None),
        ("Clara Diaz", "patient3@example.com", patient_pw, "patient", "+1-555-0203", None)
    ]
    for p in patients:
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone, specialty)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', p)

    conn.commit()

    # Retrieve inserted doctor IDs
    cursor.execute("SELECT id, name FROM users WHERE role = 'doctor'")
    doc_rows = cursor.fetchall()
    doc_ids = {row['name']: row['id'] for row in doc_rows}

    # Retrieve inserted patient IDs
    cursor.execute("SELECT id, name FROM users WHERE role = 'patient'")
    pat_rows = cursor.fetchall()
    pat_ids = {row['name']: row['id'] for row in pat_rows}

    # 4. Doctor Schedules (Monday to Friday, 09:00 - 17:00, 30 min duration)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for d_name, d_id in doc_ids.items():
        for day in days:
            cursor.execute('''
                INSERT INTO doctor_schedules (doctor_id, day_of_week, start_time, end_time, slot_duration)
                VALUES (?, ?, ?, ?, ?)
            ''', (d_id, day, "09:00", "17:00", 30))

    # 5. Synthetic Completed Appointments & Medical Records
    # Historical appointment for Alex Johnson with Dr. Alex Demo
    cursor.execute('''
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
        VALUES (?, ?, '2026-09-18', '10:00', 'Annual Health Wellness Checkup', 'Completed')
    ''', (pat_ids['Alex Johnson'], doc_ids['Dr. Alex Demo']))
    appt1_id = cursor.lastrowid

    # Create dummy medical record for appt1
    rec1_content = f"{pat_ids['Alex Johnson']}:{doc_ids['Dr. Alex Demo']}:2026-09-18:Routine Checkup:Normal:Genesis"
    rec1_hash = hashlib.sha256(rec1_content.encode('utf-8')).hexdigest()
    cursor.execute('''
        INSERT INTO medical_records (patient_id, doctor_id, appointment_id, diagnosis, prescription, notes, record_date, record_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        pat_ids['Alex Johnson'],
        doc_ids['Dr. Alex Demo'],
        appt1_id,
        "Routine Health Screening — Normal Vitals",
        "Vitamin D3 1000 IU daily, Multivitamin once daily.",
        "Patient shows optimal blood pressure (118/76 mmHg) and clear lung sounds. Continue regular exercise.",
        "2026-09-18",
        rec1_hash
    ))

    # Historical appointment with Dr. Emily Stone (Cardiology)
    cursor.execute('''
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
        VALUES (?, ?, '2026-10-02', '14:30', 'Mild heart palpitations after running', 'Completed')
    ''', (pat_ids['Alex Johnson'], doc_ids['Dr. Emily Stone']))
    appt2_id = cursor.lastrowid

    rec2_content = f"{pat_ids['Alex Johnson']}:{doc_ids['Dr. Emily Stone']}:2026-10-02:Mild Palpitations:Metoprolol:{rec1_hash}"
    rec2_hash = hashlib.sha256(rec2_content.encode('utf-8')).hexdigest()
    cursor.execute('''
        INSERT INTO medical_records (patient_id, doctor_id, appointment_id, diagnosis, prescription, notes, record_date, record_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        pat_ids['Alex Johnson'],
        doc_ids['Dr. Emily Stone'],
        appt2_id,
        "Benign Sinus Tachycardia (Synthetic Diagnosis)",
        "Hydration therapy, reduce caffeine intake. Follow-up in 30 days if symptoms persist.",
        "ECG rhythm strip demonstrates normal sinus rhythm with occasional sinus tachycardia during exertion.",
        "2026-10-02",
        rec2_hash
    ))

    # Upcoming confirmed appointment for Alex Johnson
    cursor.execute('''
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
        VALUES (?, ?, '2026-10-08', '10:00', 'Cardiology Follow-Up', 'Confirmed')
    ''', (pat_ids['Alex Johnson'], doc_ids['Dr. Emily Stone']))

    # Upcoming pending appointment for Bob Miller
    cursor.execute('''
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
        VALUES (?, ?, '2026-10-09', '11:30', 'Migraine and headache assessment', 'Pending')
    ''', (pat_ids['Bob Miller'], doc_ids['Dr. Sarah Chen']))

    # 6. Initial Audit Logs with Cryptographic Hash Chain
    genesis_entry = "0000000000000000000000000000000000000000000000000000000000000000"
    
    events = [
        (1, "SYSTEM_INIT", "DATABASE", "0", "Allowed", "System schema and synthetic records initialized", genesis_entry),
        (pat_ids['Alex Johnson'], "LOGIN_SUCCESS", "AUTH", str(pat_ids['Alex Johnson']), "Allowed", "Patient authenticated successfully", None),
        (pat_ids['Alex Johnson'], "APPOINTMENT_CREATED", "APPOINTMENT", str(appt1_id), "Allowed", "Booked General Consultation slot", None),
        (doc_ids['Dr. Alex Demo'], "APPOINTMENT_CONFIRMED", "APPOINTMENT", str(appt1_id), "Allowed", "Doctor confirmed booking", None),
        (doc_ids['Dr. Alex Demo'], "MEDICAL_RECORD_CREATED", "MEDICAL_RECORD", "1", "Allowed", "Generated synthetic consultation record", None),
    ]

    last_hash = genesis_entry
    for u_id, action, r_type, r_id, result, details, _ in events:
        log_payload = f"{last_hash}:{u_id}:{action}:{r_type}:{r_id}:{result}:{details}"
        curr_hash = hashlib.sha256(log_payload.encode('utf-8')).hexdigest()
        cursor.execute('''
            INSERT INTO audit_logs (user_id, action, resource_type, resource_id, result, details, prev_hash, current_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (u_id, action, r_type, r_id, result, details, last_hash, curr_hash))
        last_hash = curr_hash

    conn.commit()


import re
from datetime import datetime, date

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def validate_email(email):
    """Validate email address format and length."""
    if not email or len(email) > 120:
        return False, "Email address is required and must not exceed 120 characters."
    if not EMAIL_REGEX.match(email.strip()):
        return False, "Please enter a valid email address (e.g., user@example.com)."
    return True, None

def validate_password_strength(password):
    """
    Enforce strong password requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special symbol
    """
    if not password:
        return False, "Password cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    if not re.search(r'[A-Z]', password):
        return False, "Password must include at least one uppercase letter (A-Z)."
    if not re.search(r'[a-z]', password):
        return False, "Password must include at least one lowercase letter (a-z)."
    if not re.search(r'[0-9]', password):
        return False, "Password must include at least one number (0-9)."
    if not re.search(r'[\W_]', password):
        return False, "Password must include at least one special character (!@#$%^&* etc.)."
    return True, None

def validate_name(name):
    """Validate human names."""
    if not name or len(name.strip()) < 2:
        return False, "Name must be at least 2 characters long."
    if len(name.strip()) > 80:
        return False, "Name cannot exceed 80 characters."
    if re.search(r'[<>{}\[\]\\]', name):
        return False, "Name contains prohibited special characters."
    return True, None

def validate_appointment_date(date_str):
    """Ensure appointment date is valid ISO format and not in the past."""
    try:
        appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False, "Invalid date format. Use YYYY-MM-DD.", None
    
    today = date.today()
    if appt_date < today:
        return False, "Appointments cannot be booked for past dates.", None
    
    # Maximum 60 days in advance
    if (appt_date - today).days > 60:
        return False, "Appointments can only be scheduled up to 60 days in advance.", None
        
    return True, None, appt_date

def validate_appointment_time(time_str):
    """Validate time string format (HH:MM)."""
    try:
        t = datetime.strptime(time_str, "%H:%M").time()
        return True, None, t
    except (ValueError, TypeError):
        return False, "Invalid time format. Use HH:MM.", None

def validate_integer_id(val):
    """Ensure an ID parameter is a positive integer."""
    try:
        val_int = int(val)
        if val_int <= 0:
            return False, None
        return True, val_int
    except (ValueError, TypeError):
        return False, None

def sanitize_text(text, max_len=1000):
    """Basic sanitization and whitespace trimming."""
    if not text:
        return ""
    clean = text.strip()
    return clean[:max_len]


from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.users import get_user_by_email, register_patient, get_user_by_id
from security.auth import verify_password, login_user, logout_user, is_login_throttled, record_login_attempt
from security.audit import log_audit_event

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User authentication with rate limiting and generic error messages."""
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'patient':
            return redirect(url_for('patient.dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Check rate limiting / brute force lockout
        if is_login_throttled(email):
            flash("Too many failed login attempts. Please wait 5 minutes before trying again.", "danger")
            log_audit_event(
                user_id=None,
                action="LOGIN_THROTTLED",
                resource_type="AUTH",
                resource_id=email,
                result="Denied",
                details="Rate limit threshold reached for IP/account"
            )
            return render_template('auth/login.html')

        user = get_user_by_email(email)
        if not user or not verify_password(user['password_hash'], password):
            record_login_attempt(email, success=False)
            log_audit_event(
                user_id=user['id'] if user else None,
                action="LOGIN_FAILURE",
                resource_type="AUTH",
                resource_id=email,
                result="Denied",
                details="Invalid credentials supplied"
            )
            # Generic error message to prevent user enumeration
            flash("Invalid email or password. Please verify your credentials.", "danger")
            return render_template('auth/login.html')

        if not user['is_active']:
            flash("This account is currently deactivated. Please contact an administrator.", "warning")
            return render_template('auth/login.html')

        record_login_attempt(email, success=True)
        login_user(user)
        flash(f"Welcome back, {user['name']}!", "success")

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

        if user['role'] == 'patient':
            return redirect(url_for('patient.dashboard'))
        elif user['role'] == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Patient registration endpoint."""
    if 'user_id' in session:
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        phone = request.form.get('phone', '')

        success, result = register_patient(name, email, password, phone)
        if not success:
            flash(result, "danger")
            return render_template('auth/register.html')

        flash("Registration successful! You may now sign in with your credentials.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    """Sign out user and clear secure session."""
    logout_user()
    flash("You have been securely signed out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/demo-login/<role>')
def demo_login(role):
    """
    Demo Fast-Switch: Allows judges and evaluators to quickly log into seeded accounts.
    Only available in demo mode.
    """
    doctor_id = request.args.get('id', type=int)
    if role.lower() == 'doctor' and doctor_id:
        user = get_user_by_id(doctor_id)
        if user and user['role'] == 'doctor':
            login_user(user)
            flash(f"Signed in as {user['name']} ({user['specialty']})", "info")
            return redirect(url_for('doctor.dashboard'))

    demo_emails = {
        'patient': 'patient@example.com',
        'doctor': 'doctor@medidesk.com',
        'admin': 'admin@medidesk.com'
    }
    target_email = demo_emails.get(role.lower())
    if not target_email:
        flash("Invalid demo role specified.", "warning")
        return redirect(url_for('auth.login'))

    user = get_user_by_email(target_email)
    if user:
        login_user(user)
        flash(f"Signed in via Demo Shortcut as {user['name']} ({user['role'].title()})", "info")
        if user['role'] == 'patient':
            return redirect(url_for('patient.dashboard'))
        elif user['role'] == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))

    flash("Demo account not found.", "danger")
    return redirect(url_for('auth.login'))


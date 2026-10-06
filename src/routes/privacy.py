from flask import Blueprint, render_template, session
from security.permissions import login_required
from database.db import get_db

privacy_bp = Blueprint('privacy', __name__, url_prefix='/privacy')

@privacy_bp.route('/')
@login_required
def privacy_center():
    """Display user-friendly Privacy Center and personal account activity log."""
    user_id = session.get('user_id')
    user_role = session.get('user_role')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT action, resource_type, timestamp, result, details
        FROM audit_logs
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
    ''', (user_id,))
    recent_activity = cursor.fetchall()
    conn.close()

    return render_template('privacy/privacy_center.html', recent_activity=recent_activity)


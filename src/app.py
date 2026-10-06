import os
import sys

# Ensure current src directory is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, render_template, request, session, redirect, url_for
from config import Config
from database.db import init_db

# Import Blueprints
from routes.auth import auth_bp
from routes.patient import patient_bp
from routes.doctor import doctor_bp
from routes.admin import admin_bp
from routes.assistant import assistant_bp
from routes.privacy import privacy_bp

def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static')
    )
    app.config.from_object(config_class)

    # Initialize Database schema and seed data
    init_db()

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(privacy_bp)

    # Landing Page Route
    @app.route('/')
    def index():
        return render_template('index.html')

    # Security Headers Middleware
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Global Template Context
    @app.context_processor
    def inject_global_vars():
        return {
            'demo_banner': app.config.get('SYNTHETIC_DATA_BANNER', 'Demo Environment — Synthetic Data Only.'),
            'demo_mode': app.config.get('DEMO_MODE', True)
        }

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting MediDesk server at http://127.0.0.1:{port}...")
    app.run(host='127.0.0.1', port=port, debug=False)

"""
app.py
Application factory and server entrypoint for Smart Campus Complaint & Maintenance Portal.
"""

from flask import Flask, redirect, url_for, session, render_template
from flask_wtf.csrf import CSRFProtect
from config import Config
from utils.db import close_db

csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize CSRF Protection
    csrf.init_app(app)

    # Register Database Teardown
    app.teardown_appcontext(close_db)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.admin import admin_bp
    from routes.staff import staff_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)

    # Root Route: Intelligent Role-Based Redirection
    @app.route('/')
    def index():
        if session.get('user_id'):
            role = session.get('role')
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif role == 'faculty':
                return redirect(url_for('student.faculty_dashboard'))
            else:
                return redirect(url_for('student.student_dashboard'))
        return redirect(url_for('auth.login'))

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


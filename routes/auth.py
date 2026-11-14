"""
routes/auth.py
Authentication routes: login, registration, and logout.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from utils.db import get_db
from utils.validators import ALLOWED_PUBLIC_ROLES

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'staff':
            return redirect(url_for('staff.dashboard'))
        elif role == 'faculty':
            return redirect(url_for('student.faculty_dashboard'))
        return redirect(url_for('student.student_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please provide both email address and password.', 'danger')
            return render_template('auth/login.html')

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password_hash'], password):
            # Session assignment
            session.clear()
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            session['department_id'] = user['department_id']

            flash(f"Welcome back, {user['name']}!", 'success')

            # Role-based redirection
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)

            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user['role'] == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif user['role'] == 'faculty':
                return redirect(url_for('student.faculty_dashboard'))
            else:
                return redirect(url_for('student.student_dashboard'))
        else:
            flash('Invalid email credentials or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        requested_role = request.form.get('role', 'student').strip().lower()

        # Security check: never allow admin or staff via public registration
        if requested_role not in ALLOWED_PUBLIC_ROLES:
            requested_role = 'student'

        # Validation
        if not name or len(name) < 2:
            flash('Full name must be at least 2 characters.', 'danger')
            return render_template('auth/register.html')

        if not email or '@' not in email or '.' not in email:
            flash('Please enter a valid campus email address.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            flash('An account with this email address is already registered.', 'warning')
            return render_template('auth/register.html')

        pw_hash = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (name, email, pw_hash, requested_role)
        )
        db.commit()
        cursor.close()

        flash('Registration successful! You may now sign in with your credentials.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been securely signed out.', 'info')
    return redirect(url_for('auth.login'))


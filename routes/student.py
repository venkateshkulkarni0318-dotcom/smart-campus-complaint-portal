"""
routes/student.py
Student and Faculty routes: dashboard, complaint submission, tracking, and details.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from utils.auth import login_required, role_required
from utils.db import get_db
from utils.validators import validate_complaint_input, ALLOWED_CATEGORIES, ALLOWED_PRIORITIES
from datetime import datetime

student_bp = Blueprint('student', __name__)


@student_bp.route('/student/dashboard')
@role_required('student')
def student_dashboard():
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Calculate real-time stats for the authenticated student
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved
        FROM complaints
        WHERE user_id = %s
    """, (user_id,))
    stats = cursor.fetchone() or {'total': 0, 'pending': 0, 'in_progress': 0, 'resolved': 0}

    # Fetch recent 10 complaints
    cursor.execute("""
        SELECT c.*, d.department_name
        FROM complaints c
        LEFT JOIN departments d ON c.department_id = d.department_id
        WHERE c.user_id = %s
        ORDER BY c.created_at DESC
        LIMIT 10
    """, (user_id,))
    recent_complaints = cursor.fetchall()
    cursor.close()

    return render_template(
        'student/dashboard.html',
        stats=stats,
        complaints=recent_complaints,
        active_page='student_dashboard'
    )


@student_bp.route('/faculty/dashboard')
@role_required('faculty')
def faculty_dashboard():
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved
        FROM complaints
        WHERE user_id = %s
    """, (user_id,))
    stats = cursor.fetchone() or {'total': 0, 'pending': 0, 'in_progress': 0, 'resolved': 0}

    cursor.execute("""
        SELECT c.*, d.department_name
        FROM complaints c
        LEFT JOIN departments d ON c.department_id = d.department_id
        WHERE c.user_id = %s
        ORDER BY c.created_at DESC
        LIMIT 10
    """, (user_id,))
    recent_complaints = cursor.fetchall()
    cursor.close()

    return render_template(
        'student/faculty_dashboard.html',
        stats=stats,
        complaints=recent_complaints,
        active_page='faculty_dashboard'
    )


@student_bp.route('/complaints/new', methods=['GET', 'POST'])
@role_required('student', 'faculty')
def new_complaint():
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        building = request.form.get('building', '').strip()
        floor = request.form.get('floor', '').strip() or None
        room = request.form.get('room', '').strip()

        is_valid, error_msg = validate_complaint_input(category, description, building, floor, room)
        if not is_valid:
            flash(error_msg, 'danger')
            return render_template(
                'complaints/new.html',
                categories=sorted(ALLOWED_CATEGORIES),
                form_data=request.form,
                active_page='new_complaint'
            )

        db = get_db()
        cursor = db.cursor(dictionary=True)

        try:
            # 1. Insert complaint record without ticket number
            cursor.execute("""
                INSERT INTO complaints (user_id, category, description, building, floor, room, priority, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'Medium', 'Pending')
            """, (session['user_id'], category, description, building, floor, room))

            complaint_id = cursor.lastrowid
            year = datetime.now().year
            ticket_number = f"CMP-{year}-{complaint_id:04d}"

            # 2. Update complaint with generated unique ticket number
            cursor.execute("""
                UPDATE complaints SET ticket_number = %s WHERE complaint_id = %s
            """, (ticket_number, complaint_id))

            # 3. Create initial complaint history entry
            cursor.execute("""
                INSERT INTO complaint_history (complaint_id, old_status, new_status, updated_by, remarks)
                VALUES (%s, NULL, 'Pending', %s, 'Complaint registered in portal')
            """, (complaint_id, session['user_id']))

            db.commit()
            flash(f"Complaint successfully submitted! Your ticket number is {ticket_number}.", 'success')
            return redirect(url_for('student.complaint_details', complaint_id=complaint_id))

        except Exception as err:
            db.rollback()
            flash(f"An error occurred while filing the complaint: {str(err)}", 'danger')
        finally:
            cursor.close()

    return render_template(
        'complaints/new.html',
        categories=sorted(ALLOWED_CATEGORIES),
        active_page='new_complaint'
    )


@student_bp.route('/complaints/<int:complaint_id>')
@login_required
def complaint_details(complaint_id):
    user_id = session['user_id']
    role = session['role']

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.*, u.name AS submitter_name, u.email AS submitter_email,
               d.department_name, s.name AS staff_name
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        LEFT JOIN departments d ON c.department_id = d.department_id
        LEFT JOIN users s ON c.assigned_staff_id = s.user_id
        WHERE c.complaint_id = %s
    """, (complaint_id,))
    complaint = cursor.fetchone()

    if not complaint:
        cursor.close()
        abort(404)

    # Ownership & Access Control Check
    if role in ('student', 'faculty') and complaint['user_id'] != user_id:
        cursor.close()
        abort(403)
    elif role == 'staff' and complaint['assigned_staff_id'] != user_id:
        cursor.close()
        abort(403)

    # Fetch History Timeline
    cursor.execute("""
        SELECT h.*, u.name AS updated_by_name, u.role AS updated_by_role
        FROM complaint_history h
        JOIN users u ON h.updated_by = u.user_id
        WHERE h.complaint_id = %s
        ORDER BY h.created_at ASC
    """, (complaint_id,))
    history = cursor.fetchall()
    cursor.close()

    return render_template('complaints/details.html', complaint=complaint, history=history)


@student_bp.route('/complaints/track')
@login_required
def track_complaint():
    ticket = request.args.get('ticket', '').strip().upper()
    complaint = None

    if ticket:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, d.department_name, s.name AS staff_name
            FROM complaints c
            LEFT JOIN departments d ON c.department_id = d.department_id
            LEFT JOIN users s ON c.assigned_staff_id = s.user_id
            WHERE c.ticket_number = %s
        """, (ticket,))
        complaint = cursor.fetchone()

        if complaint:
            # Enforce ownership check: student/faculty can only track their own
            role = session['role']
            if role in ('student', 'faculty') and complaint['user_id'] != session['user_id']:
                flash('Access restricted: You may only track tickets submitted by your account.', 'danger')
                complaint = None
            elif role == 'staff' and complaint['assigned_staff_id'] != session['user_id']:
                flash('Access restricted: This complaint is not assigned to your account.', 'danger')
                complaint = None
        else:
            flash(f"No complaint ticket found matching '{ticket}'.", 'warning')

        cursor.close()

    return render_template(
        'complaints/track.html',
        complaint=complaint,
        searched_ticket=ticket,
        active_page='track_complaint'
    )


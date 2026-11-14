"""
routes/admin.py
Administrator routes: system overview, complaint management, staff assignment, priority updates.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from utils.auth import role_required
from utils.db import get_db
from utils.validators import (
    validate_assignment,
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
    ALLOWED_STATUSES
)

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/dashboard')
@role_required('admin')
def dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 1. Real-time Campus Overall Counts
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status = 'Assigned' THEN 1 ELSE 0 END) AS assigned,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved
        FROM complaints
    """)
    stats = cursor.fetchone() or {'total': 0, 'pending': 0, 'assigned': 0, 'in_progress': 0, 'resolved': 0}

    # 2. Category Breakdown for Chart.js
    cursor.execute("""
        SELECT category, COUNT(*) AS count
        FROM complaints
        GROUP BY category
    """)
    category_rows = cursor.fetchall()
    category_counts = {row['category']: row['count'] for row in category_rows}

    # 3. Status Breakdown for Chart.js
    status_counts = {
        'Pending': int(stats['pending'] or 0),
        'Assigned': int(stats['assigned'] or 0),
        'In Progress': int(stats['in_progress'] or 0),
        'Resolved': int(stats['resolved'] or 0)
    }

    # 4. Recent Complaints across all campus
    cursor.execute("""
        SELECT c.*, u.name AS submitter_name, d.department_name, s.name AS staff_name
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        LEFT JOIN departments d ON c.department_id = d.department_id
        LEFT JOIN users s ON c.assigned_staff_id = s.user_id
        ORDER BY c.created_at DESC
        LIMIT 8
    """)
    recent_complaints = cursor.fetchall()
    cursor.close()

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        category_counts=category_counts,
        status_counts=status_counts,
        complaints=recent_complaints,
        active_page='admin_dashboard'
    )


@admin_bp.route('/admin/complaints')
@role_required('admin')
def complaints():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Filter parameters from query string
    status = request.args.get('status', '').strip()
    priority = request.args.get('priority', '').strip()
    category = request.args.get('category', '').strip()
    dept_id = request.args.get('department_id', '').strip()
    search = request.args.get('search', '').strip()

    query = """
        SELECT c.*, u.name AS submitter_name, u.role AS submitter_role,
               d.department_name, s.name AS staff_name
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        LEFT JOIN departments d ON c.department_id = d.department_id
        LEFT JOIN users s ON c.assigned_staff_id = s.user_id
        WHERE 1=1
    """
    params = []

    if status and status in ALLOWED_STATUSES:
        query += " AND c.status = %s"
        params.append(status)

    if priority and priority in ALLOWED_PRIORITIES:
        query += " AND c.priority = %s"
        params.append(priority)

    if category and category in ALLOWED_CATEGORIES:
        query += " AND c.category = %s"
        params.append(category)

    if dept_id and dept_id.isdigit():
        query += " AND c.department_id = %s"
        params.append(int(dept_id))

    if search:
        query += " AND (c.ticket_number LIKE %s OR c.description LIKE %s OR c.building LIKE %s OR c.room LIKE %s)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    query += " ORDER BY c.created_at DESC"

    cursor.execute(query, tuple(params))
    complaint_list = cursor.fetchall()

    # Fetch departments and staff for assignment modals
    cursor.execute("SELECT * FROM departments ORDER BY department_name")
    departments = cursor.fetchall()

    cursor.execute("""
        SELECT user_id, name, email, department_id
        FROM users
        WHERE role = 'staff'
        ORDER BY name
    """)
    staff_members = cursor.fetchall()

    cursor.close()

    return render_template(
        'admin/complaints.html',
        complaints=complaint_list,
        departments=departments,
        staff_members=staff_members,
        selected_status=status,
        selected_priority=priority,
        selected_category=category,
        selected_dept=dept_id,
        search_query=search,
        active_page='admin_complaints'
    )


@admin_bp.route('/admin/complaints/<int:complaint_id>/assign', methods=['POST'])
@role_required('admin')
def assign_complaint(complaint_id):
    department_id = request.form.get('department_id')
    staff_id = request.form.get('assigned_staff_id')
    priority = request.form.get('priority')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Check complaint existence
        cursor.execute("SELECT * FROM complaints WHERE complaint_id = %s", (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            flash('Complaint not found.', 'danger')
            return redirect(url_for('admin.complaints'))

        # 3-Layer Validation (dept exists, staff exists + is staff, staff in dept)
        is_valid, err_msg, staff_user = validate_assignment(cursor, department_id, staff_id)
        if not is_valid:
            flash(f"Assignment rejected: {err_msg}", 'danger')
            return redirect(url_for('admin.complaints'))

        old_status = complaint['status']
        new_status = 'Assigned'

        # Ensure priority is valid
        if priority not in ALLOWED_PRIORITIES:
            priority = complaint['priority']

        # Update complaint record
        cursor.execute("""
            UPDATE complaints
            SET department_id = %s,
                assigned_staff_id = %s,
                priority = %s,
                status = %s,
                updated_at = NOW()
            WHERE complaint_id = %s
        """, (department_id, staff_id, priority, new_status, complaint_id))

        # Insert audit history
        cursor.execute("""
            INSERT INTO complaint_history (complaint_id, old_status, new_status, updated_by, remarks)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            complaint_id,
            old_status,
            new_status,
            session['user_id'],
            f"Assigned to {staff_user['name']} by Administrator"
        ))

        db.commit()
        flash(f"Ticket {complaint['ticket_number']} successfully assigned to {staff_user['name']}.", 'success')

    except Exception as err:
        db.rollback()
        flash(f"Failed to assign complaint: {str(err)}", 'danger')
    finally:
        cursor.close()

    return redirect(url_for('admin.complaints'))


@admin_bp.route('/admin/complaints/<int:complaint_id>/priority', methods=['POST'])
@role_required('admin')
def update_priority(complaint_id):
    new_priority = request.form.get('priority', '').strip()
    if new_priority not in ALLOWED_PRIORITIES:
        flash('Invalid priority level selected.', 'danger')
        return redirect(url_for('admin.complaints'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE complaints SET priority = %s, updated_at = NOW() WHERE complaint_id = %s
        """, (new_priority, complaint_id))
        db.commit()
        flash('Priority updated successfully.', 'success')
    except Exception as err:
        db.rollback()
        flash(f"Error updating priority: {str(err)}", 'danger')
    finally:
        cursor.close()

    return redirect(url_for('admin.complaints'))


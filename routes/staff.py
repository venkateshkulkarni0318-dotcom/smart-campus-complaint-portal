"""
routes/staff.py
Maintenance staff routes: task dashboard and status lifecycle transitions.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from utils.auth import role_required
from utils.db import get_db
from utils.validators import ALLOWED_TRANSITIONS

staff_bp = Blueprint('staff', __name__)


@staff_bp.route('/staff/dashboard')
@role_required('staff')
def dashboard():
    staff_id = session['user_id']
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 1. Staff Specific Metrics
    cursor.execute("""
        SELECT
            COUNT(*) AS total_assigned,
            SUM(CASE WHEN status = 'Assigned' THEN 1 ELSE 0 END) AS pending_start,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved
        FROM complaints
        WHERE assigned_staff_id = %s
    """, (staff_id,))
    stats = cursor.fetchone() or {'total_assigned': 0, 'pending_start': 0, 'in_progress': 0, 'resolved': 0}

    # 2. Staff Assigned Task List
    cursor.execute("""
        SELECT c.*, u.name AS submitter_name, u.email AS submitter_email,
               d.department_name
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        LEFT JOIN departments d ON c.department_id = d.department_id
        WHERE c.assigned_staff_id = %s
        ORDER BY
            CASE
                WHEN c.status = 'In Progress' THEN 1
                WHEN c.status = 'Assigned' THEN 2
                ELSE 3
            END,
            c.created_at DESC
    """, (staff_id,))
    assigned_tasks = cursor.fetchall()
    cursor.close()

    return render_template(
        'staff/dashboard.html',
        stats=stats,
        tasks=assigned_tasks,
        active_page='staff_dashboard'
    )


@staff_bp.route('/staff/complaints/<int:complaint_id>/status', methods=['POST'])
@role_required('staff')
def update_status(complaint_id):
    staff_id = session['user_id']
    new_status = request.form.get('new_status', '').strip()
    remarks = request.form.get('remarks', '').strip()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Fetch complaint
        cursor.execute("SELECT * FROM complaints WHERE complaint_id = %s", (complaint_id,))
        complaint = cursor.fetchone()

        if not complaint:
            flash('Complaint not found.', 'danger')
            return redirect(url_for('staff.dashboard'))

        # Ownership Enforcement: staff can only update complaints assigned to them
        if complaint['assigned_staff_id'] != staff_id:
            cursor.close()
            abort(403)

        current_status = complaint['status']
        allowed_next = ALLOWED_TRANSITIONS.get((current_status, 'staff'), [])

        # Validate Status Transition
        if new_status not in allowed_next:
            flash(
                f"Unauthorized status change: '{current_status}' cannot be moved to '{new_status}'.",
                'danger'
            )
            return redirect(url_for('staff.dashboard'))

        # Enforcement: remarks required when resolving
        if new_status == 'Resolved' and not remarks:
            flash('Resolution remarks are required when marking a complaint as Resolved.', 'danger')
            return redirect(url_for('staff.dashboard'))

        # Update complaint record
        if new_status == 'Resolved':
            cursor.execute("""
                UPDATE complaints
                SET status = %s, resolution_remarks = %s, updated_at = NOW()
                WHERE complaint_id = %s
            """, (new_status, remarks, complaint_id))
        else:
            cursor.execute("""
                UPDATE complaints
                SET status = %s, updated_at = NOW()
                WHERE complaint_id = %s
            """, (new_status, complaint_id))

        # Record History Entry
        cursor.execute("""
            INSERT INTO complaint_history (complaint_id, old_status, new_status, updated_by, remarks)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            complaint_id,
            current_status,
            new_status,
            staff_id,
            remarks or f"Status shifted to {new_status} by staff"
        ))

        db.commit()
        flash(f"Status for ticket {complaint['ticket_number']} updated to {new_status}!", 'success')

    except Exception as err:
        db.rollback()
        flash(f"Failed to update task status: {str(err)}", 'danger')
    finally:
        cursor.close()

    return redirect(url_for('staff.dashboard'))


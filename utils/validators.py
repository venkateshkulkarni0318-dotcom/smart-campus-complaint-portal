"""
utils/validators.py
Input validation, sanitization, and allowlist enforcement for complaints and assignments.
"""

# Allowed Enums
ALLOWED_CATEGORIES = {
    'Electrical',
    'Plumbing',
    'Infrastructure',
    'Sanitation',
    'Classroom Equipment',
    'Other'
}

ALLOWED_PRIORITIES = {'Low', 'Medium', 'High'}

ALLOWED_STATUSES = {'Pending', 'Assigned', 'In Progress', 'Resolved'}

ALLOWED_PUBLIC_ROLES = {'student', 'faculty'}

# Status Transition Matrix: (current_status, actor_role) -> [allowed_new_statuses]
ALLOWED_TRANSITIONS = {
    ('Pending', 'admin'): ['Assigned'],        # Admin assigns pending complaint
    ('Assigned', 'admin'): ['Assigned'],       # Admin re-assigns
    ('Assigned', 'staff'): ['In Progress'],    # Staff starts task
    ('In Progress', 'staff'): ['Resolved'],    # Staff completes task
}


def validate_complaint_input(category, description, building, floor, room):
    """
    Validates user input during complaint submission.
    Returns (is_valid, error_message).
    """
    if not category or category not in ALLOWED_CATEGORIES:
        return False, f"Invalid category. Must be one of: {', '.join(sorted(ALLOWED_CATEGORIES))}."

    if not description or len(description.strip()) < 10:
        return False, "Description must be at least 10 characters long with meaningful detail."

    if len(description) > 2000:
        return False, "Description cannot exceed 2000 characters."

    if not building or len(building.strip()) < 2:
        return False, "Building name or block is required."

    if not room or len(room.strip()) < 1:
        return False, "Room number or specific location is required."

    return True, None


def validate_assignment(cursor, department_id, staff_id):
    """
    3-Layer Backend Staff Assignment Validation:
      Layer 1: Department exists.
      Layer 2: Assigned user exists and has role='staff'.
      Layer 3: Assigned staff belongs to the specified department.
    Returns (is_valid, error_message, staff_data).
    """
    try:
        dept_id = int(department_id)
        s_id = int(staff_id)
    except (ValueError, TypeError):
        return False, "Invalid department or staff identifier provided.", None

    # Layer 1: Check department existence
    cursor.execute("SELECT department_id, department_name FROM departments WHERE department_id = %s", (dept_id,))
    dept = cursor.fetchone()
    if not dept:
        return False, "Selected department does not exist in the system.", None

    # Layer 2 & 3: Check staff user existence, role, and department membership
    cursor.execute(
        "SELECT user_id, name, email, role, department_id FROM users WHERE user_id = %s",
        (s_id,)
    )
    staff = cursor.fetchone()
    if not staff:
        return False, "Selected staff member does not exist.", None

    if staff['role'] != 'staff':
        return False, f"User '{staff['name']}' does not possess the maintenance staff role.", None

    if staff['department_id'] != dept_id:
        return False, f"Staff member '{staff['name']}' does not belong to the '{dept['department_name']}' department.", None

    return True, None, staff


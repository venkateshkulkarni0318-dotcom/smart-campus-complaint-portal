"""
utils/auth.py
Authentication and Role-Based Authorization Decorators.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, abort, request


def login_required(f):
    """
    Enforces that a valid user session exists.
    Redirects unauthenticated users to /login with next param preserved.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """
    Enforces that the authenticated user possesses one of the allowed roles.
    Aborts with 403 Forbidden if unauthorized.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Please sign in to proceed.', 'warning')
                return redirect(url_for('auth.login', next=request.path))
            user_role = session.get('role')
            if user_role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


"""
utils/auth.py
Authentication and Role-Based Authorization Decorators.
"""

from functools import wraps
from urllib.parse import urlparse, urljoin
from flask import session, redirect, url_for, flash, abort, request


def is_safe_redirect_url(target):
    """
    Validates redirect URLs to prevent Open Redirect attacks.
    Explicitly rejects protocol-relative URLs (e.g. '//evil.com'), backslash bypasses ('/\\evil.com'),
    and external destination domains.
    """
    if not target or not isinstance(target, str):
        return False

    # Block protocol-relative URLs and Windows backslash tricks
    if target.startswith('//') or target.startswith('/\\') or target.startswith('\\'):
        return False

    # Ensure target belongs strictly to the local application host
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))

    return (
        test_url.scheme in ('http', 'https')
        and ref_url.netloc == test_url.netloc
        and not test_url.netloc.startswith('//')
    )


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


"""
utils/db.py
Database connection management for Flask request lifecycle using Flask g.
"""

import os
from flask import g, current_app
import mysql.connector
from config import Config


def get_db():
    """
    Returns a MySQL database connection stored on Flask application context (g).
    Reuses connection within the same request context.
    """
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=current_app.config.get('DB_HOST', Config.DB_HOST),
            port=current_app.config.get('DB_PORT', Config.DB_PORT),
            user=current_app.config.get('DB_USER', Config.DB_USER),
            password=current_app.config.get('DB_PASSWORD', Config.DB_PASSWORD),
            database=current_app.config.get('DB_NAME', Config.DB_NAME),
            autocommit=False
        )
    return g.db


def close_db(e=None):
    """
    Closes the database connection if open at the end of the request.
    """
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()


def test_db_connection():
    """
    Utility function to test database connectivity outside the request context.
    Returns (True, message) or (False, error_message).
    """
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True, "Database connection successful!"
    except mysql.connector.Error as err:
        return False, str(err)

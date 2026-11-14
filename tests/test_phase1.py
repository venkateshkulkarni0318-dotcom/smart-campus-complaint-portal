"""
tests/test_phase1.py
Automated Verification Suite for Phase 1 Deliverables:
  1. MySQL Database connection
  2. Seeded departments and user verification
  3. Flask application factory and blueprint registration
  4. Password hash verification for demo accounts
  5. Route reachability and redirect logic
"""

import sys
import os
import unittest
from werkzeug.security import check_password_hash

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
from utils.db import test_db_connection
import mysql.connector


class TestPhase1(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_db_connection(self):
        """Verify database connectivity via utils/db.py test_db_connection()"""
        success, message = test_db_connection()
        self.assertTrue(success, f"Database connection failed: {message}")

    def test_02_departments_seeded(self):
        """Verify that all 5 required departments are seeded in MySQL"""
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT department_name FROM departments ORDER BY department_id")
        depts = [row['department_name'] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        expected = [
            'Electrical',
            'Plumbing',
            'Civil / Infrastructure',
            'Sanitation',
            'IT / Classroom Equipment'
        ]
        self.assertEqual(depts, expected)

    def test_03_users_and_hashes_seeded(self):
        """Verify demo accounts exist, have correct roles and valid password hashes"""
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email, role, password_hash, department_id FROM users")
        users = {row['email']: row for row in cursor.fetchall()}
        cursor.close()
        conn.close()

        # Admin
        self.assertIn('admin@campus.edu', users)
        self.assertEqual(users['admin@campus.edu']['role'], 'admin')
        self.assertTrue(check_password_hash(users['admin@campus.edu']['password_hash'], 'Admin@2026!'))

        # Staff with department link
        self.assertIn('electrical.staff@campus.edu', users)
        self.assertEqual(users['electrical.staff@campus.edu']['role'], 'staff')
        self.assertIsNotNone(users['electrical.staff@campus.edu']['department_id'])
        self.assertTrue(check_password_hash(users['electrical.staff@campus.edu']['password_hash'], 'Staff@2026!'))

        # Student & Faculty
        self.assertIn('student@campus.edu', users)
        self.assertEqual(users['student@campus.edu']['role'], 'student')
        self.assertTrue(check_password_hash(users['student@campus.edu']['password_hash'], 'Student@2026!'))

        self.assertIn('faculty@campus.edu', users)
        self.assertEqual(users['faculty@campus.edu']['role'], 'faculty')
        self.assertTrue(check_password_hash(users['faculty@campus.edu']['password_hash'], 'Faculty@2026!'))

    def test_04_root_redirect(self):
        """Verify unauthenticated access to / redirects to /login"""
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers.get('Location', ''))

    def test_05_login_page_renders(self):
        """Verify GET /login returns 200 and renders Smart Campus form"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Smart Campus', response.data)
        self.assertIn(b'Campus Email', response.data)
        self.assertIn(b'csrf_token', response.data)

    def test_06_register_page_renders(self):
        """Verify GET /register returns 200 and renders registration form with Student/Faculty only"""
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create an Account', response.data)
        self.assertIn(b'Student', response.data)
        self.assertIn(b'Faculty Member', response.data)
        # Verify admin/staff are NOT options in the registration form
        self.assertNotIn(b'<option value="admin"', response.data)
        self.assertNotIn(b'<option value="staff"', response.data)


if __name__ == '__main__':
    unittest.main()


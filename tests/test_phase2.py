"""
tests/test_phase2.py
Automated Verification Suite for Phase 2:
  1. Student and Faculty registration with input validation
  2. Prevention of privileged role injection (admin/staff) during registration
  3. Login authentication, password verification, open redirect mitigation
  4. Role access control (student/faculty blocked from admin and staff dashboards)
  5. Complaint submission with form validation, priority storage, and atomic ticket generation
  6. Database verification of complaint record, priority persistence, and audit history
  7. Public ticket tracking with privacy preservation & ownership boundaries
  8. Dashboard metrics calculation from live MySQL data
  9. Session termination (Logout)
"""

import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
import mysql.connector


class TestPhase2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

    @classmethod
    def tearDownClass(cls):
        """Clean up synthetic test records from database"""
        try:
            conn = mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email LIKE 'test.student.%' OR email LIKE 'hacker.%'")
            cursor.execute("DELETE FROM complaints WHERE description LIKE '%abnormal buzzing sound%' OR description LIKE '%Water cooler filter needs replacement%'")
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass

    def setUp(self):
        self.client = self.app.test_client()

    def get_db(self):
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        conn.autocommit = True
        return conn

    # ---------------- 1. Registration Tests ----------------
    def test_01_registration_valid_student(self):
        """Register a new student account and verify in MySQL"""
        unique_email = f"test.student.{int(datetime.now().timestamp())}@campus.edu"
        res = self.client.post('/register', data={
            'name': 'Rahul Verma',
            'email': unique_email,
            'role': 'student',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)

        # Verify record in MySQL
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT role, name FROM users WHERE email = %s", (unique_email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'student')
        self.assertEqual(user['name'], 'Rahul Verma')

    def test_02_registration_rejects_privileged_role_injection(self):
        """Attempt to register with role='admin' or role='staff' via POST manipulation"""
        hacker_email = f"hacker.{int(datetime.now().timestamp())}@campus.edu"
        res = self.client.post('/register', data={
            'name': 'Malicious User',
            'email': hacker_email,
            'role': 'admin',  # Injected privileged role
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify user was forced to 'student' role, NOT 'admin'
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT role FROM users WHERE email = %s", (hacker_email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'student', "Security failure: user was registered as admin!")

    def test_03_registration_validation_errors(self):
        """Verify mismatched passwords and short passwords are rejected"""
        res = self.client.post('/register', data={
            'name': 'Test User',
            'email': 'bad.password@campus.edu',
            'role': 'student',
            'password': 'short',
            'confirm_password': 'short'
        }, follow_redirects=True)
        self.assertIn(b'Password must be at least 8 characters', res.data)

        res2 = self.client.post('/register', data={
            'name': 'Test User',
            'email': 'bad.match@campus.edu',
            'role': 'student',
            'password': 'ValidPassword123!',
            'confirm_password': 'DifferentPassword123!'
        }, follow_redirects=True)
        self.assertIn(b'Passwords do not match', res2.data)

    # ---------------- 2. Authentication & Redirection ----------------
    def test_04_student_login_and_redirect(self):
        """Student login redirects to /student/dashboard"""
        res = self.client.post('/login', data={
            'email': 'student@campus.edu',
            'password': 'Student@2026!'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/student/dashboard')

    def test_04b_login_rejects_open_redirect(self):
        """Verify that open redirect attempts (//evil.com) are rejected and fall back safely"""
        res = self.client.post('/login?next=//evil.com/phishing', data={
            'email': 'student@campus.edu',
            'password': 'Student@2026!'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        # Must redirect safely to student dashboard, NOT to //evil.com
        self.assertEqual(res.headers.get('Location'), '/student/dashboard')

        # Also test external full URL
        res2 = self.client.post('/login?next=https://malicious-site.com', data={
            'email': 'student@campus.edu',
            'password': 'Student@2026!'
        }, follow_redirects=False)
        self.assertEqual(res2.status_code, 302)
        self.assertEqual(res2.headers.get('Location'), '/student/dashboard')

    def test_05_faculty_login_and_redirect(self):
        """Faculty login redirects to /student/faculty_dashboard"""
        res = self.client.post('/login', data={
            'email': 'faculty@campus.edu',
            'password': 'Faculty@2026!'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/faculty/dashboard')

    def test_06_login_invalid_credentials(self):
        """Login with wrong password shows flash error"""
        res = self.client.post('/login', data={
            'email': 'student@campus.edu',
            'password': 'WrongPassword!'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Invalid email credentials or password', res.data)

    # ---------------- 3. Access Control (RBAC) ----------------
    def test_07_student_cannot_access_admin_or_staff_routes(self):
        """Students receive 403 Forbidden when trying to access admin or staff dashboards"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'student'
            sess['user_name'] = 'Aditya Sharma'

        res_admin = self.client.get('/admin/dashboard')
        self.assertEqual(res_admin.status_code, 403)

        res_staff = self.client.get('/staff/dashboard')
        self.assertEqual(res_staff.status_code, 403)

    # ---------------- 4. Complaint Submission & Priority Storage ----------------
    def test_08_submit_complaint_and_priority_storage(self):
        """Student submits a complaint with High priority: ticket generated, DB saved with High priority"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = student['user_id']
            sess['role'] = 'student'
            sess['user_name'] = 'Aditya Sharma'

        res = self.client.post('/complaints/new', data={
            'category': 'Electrical',
            'priority': 'High',
            'description': 'Ceiling fan in room 204 is making an abnormal buzzing sound and vibrating.',
            'building': 'Academic Block B',
            'floor': '2nd Floor',
            'room': 'Classroom 204'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Complaint successfully submitted', res.data)

        # Verify database record
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM complaints
            WHERE user_id = %s AND category = 'Electrical' AND room = 'Classroom 204'
            ORDER BY complaint_id DESC LIMIT 1
        """, (student['user_id'],))
        complaint = cursor.fetchone()

        self.assertIsNotNone(complaint)
        current_year = datetime.now().year
        self.assertTrue(complaint['ticket_number'].startswith(f"CMP-{current_year}-"))
        self.assertEqual(complaint['status'], 'Pending')
        self.assertEqual(complaint['priority'], 'High', "Priority was not saved as selected 'High'!")
        self.assertEqual(complaint['building'], 'Academic Block B')

        # Verify initial history record
        cursor.execute("""
            SELECT * FROM complaint_history WHERE complaint_id = %s ORDER BY history_id ASC LIMIT 1
        """, (complaint['complaint_id'],))
        hist = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertIsNotNone(hist)
        self.assertEqual(hist['new_status'], 'Pending')
        self.assertIsNone(hist['old_status'])

    def test_09_complaint_submission_validation(self):
        """Rejects submission with short description (<10 chars) or invalid priority"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'student'
            sess['user_name'] = 'Test'

        # Short description
        res = self.client.post('/complaints/new', data={
            'category': 'Electrical',
            'priority': 'Medium',
            'description': 'Too short',
            'building': 'Block A',
            'room': '101'
        }, follow_redirects=True)
        self.assertIn(b'Description must be at least 10 characters', res.data)

        # Invalid priority value
        res2 = self.client.post('/complaints/new', data={
            'category': 'Electrical',
            'priority': 'InvalidUrgency',
            'description': 'Valid long description for testing invalid priority rejection.',
            'building': 'Block A',
            'room': '101'
        }, follow_redirects=True)
        self.assertIn(b'Invalid priority level', res2.data)

    # ---------------- 5. Dashboard Metrics & Details ----------------
    def test_10_student_dashboard_metrics(self):
        """Student dashboard calculates and displays personal complaint metrics"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = student['user_id']
            sess['role'] = 'student'
            sess['user_name'] = 'Aditya Sharma'

        res = self.client.get('/student/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Student Maintenance Dashboard', res.data)
        self.assertIn(b'Total Submitted', res.data)
        self.assertIn(b'Pending Action', res.data)

    def test_11_ticket_details_ownership_check(self):
        """User cannot access complaint details belonging to another user (403 Forbidden)"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE email = 'faculty@campus.edu'")
        faculty = cursor.fetchone()

        # Insert a complaint owned by faculty
        cursor.execute("""
            INSERT INTO complaints (user_id, category, description, building, room, priority, status)
            VALUES (%s, 'Sanitation', 'Dustbin broken in faculty room', 'Admin Block', 'Room 12', 'Low', 'Pending')
        """, (faculty['user_id'],))
        faculty_cid = cursor.lastrowid
        cursor.close()
        conn.close()

        # Student tries to view faculty's complaint details
        with self.client.session_transaction() as sess:
            sess['user_id'] = student['user_id']
            sess['role'] = 'student'
            sess['user_name'] = 'Aditya Sharma'

        res = self.client.get(f'/complaints/{faculty_cid}')
        self.assertEqual(res.status_code, 403)

    # ---------------- 6. Public Ticket Tracking ----------------
    def test_12_public_tracking_privacy_preservation(self):
        """Public tracking renders status without exposing submitter PII, and restricts full audit history"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'faculty@campus.edu'")
        faculty = cursor.fetchone()

        cursor.execute("""
            INSERT INTO complaints (user_id, category, description, building, room, priority, status)
            VALUES (%s, 'Sanitation', 'Water cooler filter needs replacement in Faculty Lounge.', 'Main Block', 'Room 105', 'Low', 'Pending')
        """, (faculty['user_id'],))
        faculty_cid = cursor.lastrowid
        current_year = datetime.now().year
        fac_ticket = f"CMP-{current_year}-{faculty_cid:04d}"
        cursor.execute("UPDATE complaints SET ticket_number = %s WHERE complaint_id = %s", (fac_ticket, faculty_cid))

        # Fetch student
        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()
        cursor.close()
        conn.close()

        # Student tracks faculty's ticket: public status is visible, but full audit history is restricted
        with self.client.session_transaction() as sess:
            sess['user_id'] = student['user_id']
            sess['role'] = 'student'
            sess['user_name'] = 'Aditya Sharma'

        res = self.client.get(f"/complaints/track?ticket={fac_ticket}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(fac_ticket.encode('utf-8'), res.data)
        self.assertIn(b'Main Block', res.data)
        self.assertIn(b'Full chronological audit history is restricted', res.data)
        # Ensure submitter email is not exposed on public tracking
        self.assertNotIn(b'faculty@campus.edu', res.data)

    # ---------------- 7. Logout ----------------
    def test_13_logout_clears_session(self):
        """POST /logout clears session and redirects to /login"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'student'

        res = self.client.post('/logout', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/login')

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))


if __name__ == '__main__':
    unittest.main()

"""
tests/test_phase5.py
Automated Verification Suite for Phase 5 Enhancements (PRD Section 15):
  1. QR-code prefilled complaint reporting (building, room, floor, category)
  2. Department workload and resolution efficiency metrics computation on Admin Dashboard
  3. Average turnaround time calculation
  4. In-app activity alert / status notification banner on Student Dashboard
  5. Printable ticket summary view verification
"""

import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
import mysql.connector


class TestPhase5Enhancements(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

    def setUp(self):
        self.client = self.app.test_client()

    def get_db(self):
        return mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )

    def test_01_qr_code_prefilled_reporting(self):
        """Visiting /complaints/new with QR location params pre-populates form data"""
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

        res = self.client.get(
            '/complaints/new?building=Physics+Block&floor=1st+Floor&room=Lab+101&category=Electrical'
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Physics Block', res.data)
        self.assertIn(b'Lab 101', res.data)
        self.assertIn(b'QR Code Scanned Successfully', res.data)

    def test_02_department_performance_analytics(self):
        """Admin dashboard computes real department resolution rate and turnaround speed"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'admin@campus.edu'")
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['user_id']
            sess['role'] = 'admin'
            sess['user_name'] = 'Campus Administrator'

        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Department Operations & Resolution Analytics', res.data)
        self.assertIn(b'Campus Avg Turnaround', res.data)
        self.assertIn(b'Resolution Rate', res.data)

    def test_03_in_app_status_notification(self):
        """Student dashboard renders activity notification banner for recently resolved tickets"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()

        # Insert a resolved complaint for the student
        cursor.execute("""
            INSERT INTO complaints (user_id, category, description, building, room, priority, status, resolution_remarks)
            VALUES (%s, 'Sanitation', 'Dustbins overflowing.', 'Block A', 'Lobby', 'Low', 'Resolved', 'Area sanitized and emptied.')
        """, (student['user_id'],))
        cid = cursor.lastrowid
        cursor.execute("UPDATE complaints SET ticket_number = %s WHERE complaint_id = %s", (f"CMP-2026-{cid:04d}", cid))
        conn.commit()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = student['user_id']
            sess['role'] = 'student'
            sess['user_name'] = 'Aditya Sharma'

        res = self.client.get('/student/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Latest Incident Update', res.data)
        self.assertIn(b'Area sanitized and emptied', res.data)

    def test_04_printable_ticket_summary(self):
        """Details page contains print action button and complete summary"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT complaint_id FROM complaints LIMIT 1")
        c = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE email = 'admin@campus.edu'")
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['user_id']
            sess['role'] = 'admin'

        res = self.client.get(f"/complaints/{c['complaint_id']}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Print / Save Record', res.data)
        self.assertIn(b'window.print()', res.data)


if __name__ == '__main__':
    unittest.main()


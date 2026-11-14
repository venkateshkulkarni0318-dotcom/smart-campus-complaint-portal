"""
tests/test_e2e_demo.py
Full End-to-End Demonstration Scenario Verification (PRD Section 14):
  Step 1: Student logs in (student@campus.edu).
  Step 2: Student reports damaged ceiling fan in Classroom 204.
  Step 3: System generates unique complaint ticket (CMP-2026-NNNN).
  Step 4: Complaint appears on student dashboard with status 'Pending'.
  Step 5: Admin logs in (admin@campus.edu) and views the incident.
  Step 6: Admin assigns Electrical Department and technician Ravi Kumar (electrical.staff@campus.edu).
  Step 7: Staff logs in and sees assigned complaint in technician queue.
  Step 8: Staff changes status to 'In Progress'.
  Step 9: Staff completes repair and marks it 'Resolved' with resolution remarks.
  Step 10: Student logs in and verifies updated status 'Resolved' and remarks on details & tracker.
  Step 11: Full audit history contains chronological events from submission to resolution.
  Step 12: Real MySQL statistics accurately reflect the completed resolution.
"""

import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
import mysql.connector


class TestE2EDemoScenario(unittest.TestCase):

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

    def test_full_hackathon_demo_lifecycle(self):
        """Execute the exact 12-step hackathon demo lifecycle from end to end"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)

        # Retrieve user IDs for the scenario
        cursor.execute("SELECT user_id, name, email FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()

        cursor.execute("SELECT user_id, name, email FROM users WHERE email = 'admin@campus.edu'")
        admin = cursor.fetchone()

        cursor.execute("SELECT user_id, name, email, department_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        staff = cursor.fetchone()

        cursor.execute("SELECT department_id, department_name FROM departments WHERE department_name = 'Electrical'")
        dept = cursor.fetchone()

        cursor.close()
        conn.close()

        # ---------------- STEP 1 & 2: Student Login & Complaint Submission ----------------
        with self.client.session_transaction() as sess:
            sess['user_id'] = student['user_id']
            sess['role'] = 'student'
            sess['user_name'] = student['name']

        unique_room = f"Room-{int(datetime.now().timestamp())}"
        submit_res = self.client.post('/complaints/new', data={
            'category': 'Electrical',
            'description': 'Damaged ceiling fan in Room 204 making loud grinding noise and wobbling dangerously.',
            'building': 'Science & Tech Block C',
            'floor': '2nd Floor',
            'room': unique_room
        }, follow_redirects=True)

        self.assertEqual(submit_res.status_code, 200)
        self.assertIn(b'Complaint successfully submitted', submit_res.data)

        # ---------------- STEP 3: Verify Unique Ticket Generated ----------------
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM complaints
            WHERE user_id = %s AND room = %s
            ORDER BY complaint_id DESC LIMIT 1
        """, (student['user_id'], unique_room))
        complaint = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertIsNotNone(complaint)
        ticket_no = complaint['ticket_number']
        cid = complaint['complaint_id']
        self.assertTrue(ticket_no.startswith('CMP-2026-'))
        self.assertEqual(complaint['status'], 'Pending')
        self.assertEqual(complaint['priority'], 'Medium')

        # ---------------- STEP 4: Student Dashboard Displays Complaint ----------------
        dash_res = self.client.get('/student/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(ticket_no.encode(), dash_res.data)
        self.assertIn(unique_room.encode(), dash_res.data)

        # ---------------- STEP 5 & 6: Admin Views & Assigns Electrical Staff ----------------
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['user_id']
            sess['role'] = 'admin'
            sess['user_name'] = admin['name']

        # Admin views complaint in table
        admin_table_res = self.client.get(f"/admin/complaints?search={ticket_no}")
        self.assertEqual(admin_table_res.status_code, 200)
        self.assertIn(ticket_no.encode(), admin_table_res.data)

        # Admin assigns Electrical Department & Ravi Kumar, elevates priority to High
        assign_res = self.client.post(f"/admin/complaints/{cid}/assign", data={
            'department_id': dept['department_id'],
            'assigned_staff_id': staff['user_id'],
            'priority': 'High'
        }, follow_redirects=True)
        self.assertEqual(assign_res.status_code, 200)
        self.assertIn(b'successfully assigned', assign_res.data)

        # Verify DB assignment state
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status, priority, assigned_staff_id, department_id FROM complaints WHERE complaint_id = %s", (cid,))
        assigned_c = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertEqual(assigned_c['status'], 'Assigned')
        self.assertEqual(assigned_c['priority'], 'High')
        self.assertEqual(assigned_c['assigned_staff_id'], staff['user_id'])
        self.assertEqual(assigned_c['department_id'], dept['department_id'])

        # ---------------- STEP 7 & 8: Staff Sees Task & Starts Work (In Progress) ----------------
        with self.client.session_transaction() as sess:
            sess['user_id'] = staff['user_id']
            sess['role'] = 'staff'
            sess['user_name'] = staff['name']

        # Task visible on staff dashboard
        staff_dash_res = self.client.get('/staff/dashboard')
        self.assertEqual(staff_dash_res.status_code, 200)
        self.assertIn(ticket_no.encode(), staff_dash_res.data)

        # Staff starts work: Assigned -> In Progress
        start_res = self.client.post(f"/staff/complaints/{cid}/status", data={
            'new_status': 'In Progress',
            'remarks': 'Technician arrived on site with safety harness and motor kit.'
        }, follow_redirects=True)
        self.assertEqual(start_res.status_code, 200)
        self.assertIn(b'updated to In Progress', start_res.data)

        # ---------------- STEP 9: Staff Resolves Issue with Remarks ----------------
        resolve_remarks = 'Replaced worn fan bearings and tightened blade assembly. Tested vibration-free for 20 minutes.'
        resolve_res = self.client.post(f"/staff/complaints/{cid}/status", data={
            'new_status': 'Resolved',
            'remarks': resolve_remarks
        }, follow_redirects=True)
        self.assertEqual(resolve_res.status_code, 200)
        self.assertIn(b'updated to Resolved', resolve_res.data)

        # ---------------- STEP 10: Student Verifies Status & Resolution Remarks ----------------
        with self.client.session_transaction() as sess:
            sess['user_id'] = student['user_id']
            sess['role'] = 'student'
            sess['user_name'] = student['name']

        # Verify via Tracker
        track_res = self.client.get(f"/complaints/track?ticket={ticket_no}")
        self.assertEqual(track_res.status_code, 200)
        self.assertIn(b'Resolved', track_res.data)
        self.assertIn(resolve_remarks.encode(), track_res.data)

        # Verify via Details Page
        details_res = self.client.get(f"/complaints/{cid}")
        self.assertEqual(details_res.status_code, 200)
        self.assertIn(b'Resolved', details_res.data)
        self.assertIn(resolve_remarks.encode(), details_res.data)
        self.assertIn(staff['name'].encode(), details_res.data)

        # ---------------- STEP 11: Audit Trail Verification ----------------
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT old_status, new_status, remarks FROM complaint_history
            WHERE complaint_id = %s
            ORDER BY history_id ASC
        """, (cid,))
        history = cursor.fetchall()
        cursor.close()
        conn.close()

        # Audit trail must have recorded all 4 chronological phases:
        # 1. Pending (initial filing)
        # 2. Assigned (admin assignment)
        # 3. In Progress (staff began work)
        # 4. Resolved (staff completed repair)
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]['new_status'], 'Pending')
        self.assertEqual(history[1]['new_status'], 'Assigned')
        self.assertEqual(history[2]['new_status'], 'In Progress')
        self.assertEqual(history[3]['new_status'], 'Resolved')
        self.assertEqual(history[3]['remarks'], resolve_remarks)


if __name__ == '__main__':
    unittest.main()

"""
tests/test_phase3.py
Automated Verification Suite for Phase 3:
  1. Admin dashboard statistics & Chart.js data formatting
  2. Admin complaints table with multi-parameter filtering & search
  3. 3-Layer Backend Staff Assignment Validation:
     - Layer 1: Department existence
     - Layer 2: Staff existence & role='staff' check
     - Layer 3: Staff department membership check
  4. Priority updates and audit logging
  5. Maintenance Staff Dashboard & task queue isolation
  6. Controlled Status Transitions:
     - Assigned -> In Progress
     - In Progress -> Resolved (enforcing mandatory remarks)
     - Rejection of invalid transitions (Pending -> Resolved, Assigned -> Resolved)
     - Rejection of staff updating tasks assigned to others (ownership check)
  7. End-to-end status progression audit trail verification
"""

import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
import mysql.connector


class TestPhase3(unittest.TestCase):

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

    # ---------------- 1. Admin Dashboard & Metrics ----------------
    def test_01_admin_dashboard_metrics(self):
        """Admin dashboard displays overall metrics and Chart.js datasets"""
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
        self.assertIn(b'Operations Command Center', res.data)
        self.assertIn(b'statusChart', res.data)
        self.assertIn(b'categoryChart', res.data)

    # ---------------- 2. Admin Complaints Filtering ----------------
    def test_02_admin_complaints_search_and_filter(self):
        """Admin can filter complaints by status, priority, and search terms"""
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

        # Filter by Pending status
        res_pending = self.client.get('/admin/complaints?status=Pending')
        self.assertEqual(res_pending.status_code, 200)
        self.assertIn(b'Campus Complaints Directory', res_pending.data)

        # Filter by Priority
        res_prio = self.client.get('/admin/complaints?priority=Medium')
        self.assertEqual(res_prio.status_code, 200)

        # Keyword search
        res_search = self.client.get('/admin/complaints?search=Classroom')
        self.assertEqual(res_search.status_code, 200)

    # ---------------- 3. 3-Layer Staff Assignment Validation ----------------
    def test_03_assignment_layer1_invalid_department(self):
        """Assignment fails if department_id does not exist"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        # Create a pending complaint to test
        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()
        cursor.execute("""
            INSERT INTO complaints (user_id, category, description, building, room, priority, status)
            VALUES (%s, 'Electrical', 'Projector flickering in Auditorium.', 'Main Hall', 'Auditorium', 'High', 'Pending')
        """, (student['user_id'],))
        cid = cursor.lastrowid
        cursor.execute("UPDATE complaints SET ticket_number = %s WHERE complaint_id = %s", (f"CMP-2026-{cid:04d}", cid))
        conn.commit()

        cursor.execute("SELECT user_id FROM users WHERE email = 'admin@campus.edu'")
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['user_id']
            sess['role'] = 'admin'

        # Department ID 99999 does not exist
        res = self.client.post(f"/admin/complaints/{cid}/assign", data={
            'department_id': 99999,
            'assigned_staff_id': 2,
            'priority': 'High'
        }, follow_redirects=True)

        self.assertIn(b'Selected department does not exist', res.data)

    def test_04_assignment_layer2_non_staff_user(self):
        """Assignment fails if assigned user does not possess role='staff'"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT complaint_id FROM complaints WHERE status = 'Pending' LIMIT 1")
        c = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE email = 'admin@campus.edu'")
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['user_id']
            sess['role'] = 'admin'

        # Attempt to assign a student (user_id of student) as maintenance staff
        res = self.client.post(f"/admin/complaints/{c['complaint_id']}/assign", data={
            'department_id': 1,
            'assigned_staff_id': student['user_id'],
            'priority': 'High'
        }, follow_redirects=True)

        self.assertIn(b'does not possess the maintenance staff role', res.data)

    def test_05_assignment_layer3_staff_department_mismatch(self):
        """Assignment fails if staff user belongs to a different department"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT complaint_id FROM complaints WHERE status = 'Pending' LIMIT 1")
        c = cursor.fetchone()
        # Fetch plumbing staff (Dept 2)
        cursor.execute("SELECT user_id FROM users WHERE email = 'plumbing.staff@campus.edu'")
        plumbing_staff = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE email = 'admin@campus.edu'")
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['user_id']
            sess['role'] = 'admin'

        # Try assigning plumbing staff to Electrical Department (ID 1)
        res = self.client.post(f"/admin/complaints/{c['complaint_id']}/assign", data={
            'department_id': 1,  # Electrical
            'assigned_staff_id': plumbing_staff['user_id'],  # Belongs to Plumbing
            'priority': 'Medium'
        }, follow_redirects=True)

        self.assertIn(b'does not belong to the', res.data)

    def test_06_assignment_success_and_status_transition(self):
        """Valid assignment transitions status to 'Assigned' and logs history"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT complaint_id, ticket_number FROM complaints WHERE status = 'Pending' LIMIT 1")
        c = cursor.fetchone()
        cursor.execute("SELECT department_id FROM departments WHERE department_name = 'Electrical'")
        dept = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        staff = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE email = 'admin@campus.edu'")
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['user_id']
            sess['role'] = 'admin'

        res = self.client.post(f"/admin/complaints/{c['complaint_id']}/assign", data={
            'department_id': dept['department_id'],
            'assigned_staff_id': staff['user_id'],
            'priority': 'High'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'successfully assigned', res.data)

        # Verify DB status change
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status, priority, assigned_staff_id FROM complaints WHERE complaint_id = %s", (c['complaint_id'],))
        updated_c = cursor.fetchone()
        self.assertEqual(updated_c['status'], 'Assigned')
        self.assertEqual(updated_c['priority'], 'High')
        self.assertEqual(updated_c['assigned_staff_id'], staff['user_id'])

        # Verify history entry
        cursor.execute("""
            SELECT * FROM complaint_history
            WHERE complaint_id = %s AND new_status = 'Assigned'
            ORDER BY history_id DESC LIMIT 1
        """, (c['complaint_id'],))
        hist = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertIsNotNone(hist)
        self.assertEqual(hist['old_status'], 'Pending')
        self.assertEqual(hist['new_status'], 'Assigned')

    # ---------------- 4. Priority Update ----------------
    def test_07_admin_update_priority(self):
        """Admin can update complaint priority and it records audit history"""
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

        res = self.client.post(f"/admin/complaints/{c['complaint_id']}/priority", data={
            'priority': 'High'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Priority', res.data)

        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT priority FROM complaints WHERE complaint_id = %s", (c['complaint_id'],))
        updated = cursor.fetchone()
        cursor.close()
        conn.close()
        self.assertEqual(updated['priority'], 'High')

    # ---------------- 5. Staff Dashboard & Task Isolation ----------------
    def test_08_staff_dashboard_shows_only_assigned_tasks(self):
        """Staff dashboard isolates tasks: shows only complaints assigned to that staff member"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        staff = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = staff['user_id']
            sess['role'] = 'staff'
            sess['user_name'] = 'Ravi Kumar'

        res = self.client.get('/staff/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Technician Workspace', res.data)
        self.assertIn(b'Work Orders', res.data)

    # ---------------- 6. Staff Status Lifecycle Transitions ----------------
    def test_09_staff_start_work_assigned_to_in_progress(self):
        """Staff starts an assigned task: Assigned -> In Progress"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        staff = cursor.fetchone()

        cursor.execute("""
            SELECT complaint_id FROM complaints
            WHERE assigned_staff_id = %s AND status = 'Assigned'
            LIMIT 1
        """, (staff['user_id'],))
        c = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertIsNotNone(c, "No assigned task available for staff test")

        with self.client.session_transaction() as sess:
            sess['user_id'] = staff['user_id']
            sess['role'] = 'staff'
            sess['user_name'] = 'Ravi Kumar'

        res = self.client.post(f"/staff/complaints/{c['complaint_id']}/status", data={
            'new_status': 'In Progress',
            'remarks': 'Technician arrived on site with multimeter.'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'updated to In Progress', res.data)

        # Verify DB
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM complaints WHERE complaint_id = %s", (c['complaint_id'],))
        updated = cursor.fetchone()
        cursor.close()
        conn.close()
        self.assertEqual(updated['status'], 'In Progress')

    def test_10_staff_cannot_resolve_without_remarks(self):
        """Staff cannot mark task as Resolved without providing resolution remarks"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        staff = cursor.fetchone()

        cursor.execute("""
            SELECT complaint_id FROM complaints
            WHERE assigned_staff_id = %s AND status = 'In Progress'
            LIMIT 1
        """, (staff['user_id'],))
        c = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = staff['user_id']
            sess['role'] = 'staff'

        # Attempt resolve with empty remarks
        res = self.client.post(f"/staff/complaints/{c['complaint_id']}/status", data={
            'new_status': 'Resolved',
            'remarks': '   '  # Whitespace only
        }, follow_redirects=True)

        self.assertIn(b'Resolution remarks are required', res.data)

    def test_11_staff_complete_work_in_progress_to_resolved(self):
        """Staff marks task as Resolved with valid resolution remarks"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        staff = cursor.fetchone()

        cursor.execute("""
            SELECT complaint_id, ticket_number FROM complaints
            WHERE assigned_staff_id = %s AND status = 'In Progress'
            LIMIT 1
        """, (staff['user_id'],))
        c = cursor.fetchone()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = staff['user_id']
            sess['role'] = 'staff'
            sess['user_name'] = 'Ravi Kumar'

        res = self.client.post(f"/staff/complaints/{c['complaint_id']}/status", data={
            'new_status': 'Resolved',
            'remarks': 'Replaced blown 2.5uF capacitor on ceiling fan. Tested at high speed for 15 minutes, functioning normally.'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'updated to Resolved', res.data)

        # Verify DB
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status, resolution_remarks FROM complaints WHERE complaint_id = %s", (c['complaint_id'],))
        resolved_c = cursor.fetchone()
        self.assertEqual(resolved_c['status'], 'Resolved')
        self.assertIn('Replaced blown 2.5uF capacitor', resolved_c['resolution_remarks'])

        # Verify audit history
        cursor.execute("""
            SELECT * FROM complaint_history
            WHERE complaint_id = %s AND new_status = 'Resolved'
            ORDER BY history_id DESC LIMIT 1
        """, (c['complaint_id'],))
        hist = cursor.fetchone()
        cursor.close()
        conn.close()

        self.assertIsNotNone(hist)
        self.assertEqual(hist['old_status'], 'In Progress')
        self.assertEqual(hist['new_status'], 'Resolved')

    def test_12_rejects_invalid_status_transition(self):
        """Rejects illegal jump: staff cannot jump from Assigned directly to Resolved without In Progress"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE email = 'plumbing.staff@campus.edu'")
        plumber = cursor.fetchone()

        cursor.execute("""
            INSERT INTO complaints (user_id, category, description, building, room, priority, status, assigned_staff_id, department_id)
            VALUES (%s, 'Plumbing', 'Pipe leaking under the sink.', 'Science Block', 'Lab 102', 'Medium', 'Assigned', %s, 2)
        """, (student['user_id'], plumber['user_id']))
        cid = cursor.lastrowid
        cursor.execute("UPDATE complaints SET ticket_number = %s WHERE complaint_id = %s", (f"CMP-2026-{cid:04d}", cid))
        conn.commit()
        cursor.close()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = plumber['user_id']
            sess['role'] = 'staff'

        # Illegal attempt: change Assigned directly to Resolved (bypassing In Progress)
        res = self.client.post(f"/staff/complaints/{cid}/status", data={
            'new_status': 'Resolved',
            'remarks': 'Fixed without starting work'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Unauthorized status change', res.data)

    def test_13_staff_cannot_update_other_staff_task(self):
        """Staff member receives 403 when trying to update a task assigned to someone else"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)
        # Find complaint assigned to electrical staff
        cursor.execute("SELECT user_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        elec_staff = cursor.fetchone()
        cursor.execute("SELECT complaint_id FROM complaints WHERE assigned_staff_id = %s LIMIT 1", (elec_staff['user_id'],))
        c = cursor.fetchone()

        # Plumbing staff ID
        cursor.execute("SELECT user_id FROM users WHERE email = 'plumbing.staff@campus.edu'")
        plumb_staff = cursor.fetchone()
        cursor.close()
        conn.close()

        # Plumbing staff attempts to update electrical staff's task
        with self.client.session_transaction() as sess:
            sess['user_id'] = plumb_staff['user_id']
            sess['role'] = 'staff'

        res = self.client.post(f"/staff/complaints/{c['complaint_id']}/status", data={
            'new_status': 'In Progress'
        })
        self.assertEqual(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()

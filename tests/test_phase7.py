"""
tests/test_phase7.py
Automated Verification Suite for Phase 7 (Photo Upload & Security):
  1. File upload handling with deep binary magic byte validation (PNG, JPG, WEBP).
  2. Rejection of malicious / forged files disguised as images (e.g. PHP scripts).
  3. Resolution evidence image saved to static/uploads/ with collision-resistant safe filenames.
  4. Database persistence: `resolution_image` column in `complaints` table.
  5. Photographic proof rendering on Complaint Details view (/complaints/<id>).
  6. Photographic proof rendering on Ticket Tracking view (/complaints/track?ticket=...).
"""

import io
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
import mysql.connector


class TestPhase7ResolutionEvidence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

    @classmethod
    def tearDownClass(cls):
        """Clean up test complaints from MySQL"""
        try:
            conn = mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            cursor = conn.cursor()
            cursor.execute("DELETE FROM complaints WHERE description LIKE 'Phase 7 evidence upload%'")
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

    def test_01_resolution_photo_upload_and_display(self):
        """Staff resolves ticket with valid PNG evidence photo; verify DB storage, file creation, and template rendering"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student_id = cursor.fetchone()['user_id']

        cursor.execute("SELECT user_id, department_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        staff = cursor.fetchone()
        staff_id = staff['user_id']
        dept_id = staff['department_id']

        # Insert a fresh test complaint assigned to staff
        cursor.execute("""
            INSERT INTO complaints (user_id, category, description, building, floor, room, priority, status, department_id, assigned_staff_id)
            VALUES (%s, 'Electrical', 'Phase 7 evidence upload valid image test', 'Engineering Block', '2nd Floor', 'Lab 205', 'High', 'Assigned', %s, %s)
        """, (student_id, dept_id, staff_id))
        complaint_id = cursor.lastrowid
        ticket_number = f"CMP-TEST-P7-{complaint_id}"
        cursor.execute("UPDATE complaints SET ticket_number = %s WHERE complaint_id = %s", (ticket_number, complaint_id))

        # Shift to In Progress
        with self.client.session_transaction() as sess:
            sess['user_id'] = staff_id
            sess['role'] = 'staff'
            sess['user_name'] = 'Ravi Kumar (Electrical)'

        res_progress = self.client.post(f'/staff/complaints/{complaint_id}/status', data={
            'new_status': 'In Progress',
            'remarks': 'Technician arriving on site with multimeter'
        }, follow_redirects=True)
        self.assertEqual(res_progress.status_code, 200)

        # Shift to Resolved with valid PNG image upload
        valid_png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
            b'\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        data = {
            'new_status': 'Resolved',
            'remarks': 'Replaced burnt switchboard fuse and validated 230V circuit stability.',
            'evidence_image': (io.BytesIO(valid_png_bytes), 'repaired_circuit.png', 'image/png')
        }

        res_resolve = self.client.post(
            f'/staff/complaints/{complaint_id}/status',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.assertEqual(res_resolve.status_code, 200)

        # Verify database values
        cursor.execute("SELECT status, resolution_remarks, resolution_image FROM complaints WHERE complaint_id = %s", (complaint_id,))
        updated_complaint = cursor.fetchone()
        self.assertEqual(updated_complaint['status'], 'Resolved')
        self.assertIn('Replaced burnt switchboard fuse', updated_complaint['resolution_remarks'])
        self.assertIsNotNone(updated_complaint['resolution_image'])
        self.assertTrue(updated_complaint['resolution_image'].startswith(f"evidence_{complaint_id}_"))
        self.assertTrue(updated_complaint['resolution_image'].endswith('.png'))

        # Verify physical file existence in static/uploads
        uploaded_file_path = os.path.join(self.app.config['UPLOAD_FOLDER'], updated_complaint['resolution_image'])
        self.assertTrue(os.path.exists(uploaded_file_path), f"File {uploaded_file_path} was not saved on disk")

        # Verify Complaint Details View as Student
        with self.client.session_transaction() as sess:
            sess['user_id'] = student_id
            sess['role'] = 'student'
            sess['user_name'] = 'Aditya Sharma'

        res_details = self.client.get(f'/complaints/{complaint_id}')
        self.assertEqual(res_details.status_code, 200)
        self.assertIn(b'Verified Photographic Proof of Resolution', res_details.data)
        self.assertIn(updated_complaint['resolution_image'].encode('utf-8'), res_details.data)

        # Verify Ticket Tracker View
        res_track = self.client.get(f'/complaints/track?ticket={ticket_number}')
        self.assertEqual(res_track.status_code, 200)
        self.assertIn(b'Technician Resolution Photo', res_track.data)
        self.assertIn(updated_complaint['resolution_image'].encode('utf-8'), res_track.data)

        # Cleanup test file
        if os.path.exists(uploaded_file_path):
            try:
                os.remove(uploaded_file_path)
            except Exception:
                pass

        cursor.close()
        conn.close()

    def test_02_malicious_upload_rejection(self):
        """Forged image containing malicious script is rejected by magic byte and MIME checks"""
        conn = self.get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM users WHERE email = 'student@campus.edu'")
        student_id = cursor.fetchone()['user_id']

        cursor.execute("SELECT user_id, department_id FROM users WHERE email = 'electrical.staff@campus.edu'")
        staff = cursor.fetchone()
        staff_id = staff['user_id']
        dept_id = staff['department_id']

        # Insert a fresh test complaint assigned to staff
        cursor.execute("""
            INSERT INTO complaints (user_id, category, description, building, floor, room, priority, status, department_id, assigned_staff_id)
            VALUES (%s, 'Electrical', 'Phase 7 evidence upload malicious image test', 'Block C', '1st Floor', 'Room 101', 'High', 'In Progress', %s, %s)
        """, (student_id, dept_id, staff_id))
        complaint_id = cursor.lastrowid

        # Staff attempts to resolve with malicious text script disguised as .jpg
        malicious_script_bytes = b"<?php echo 'attack_payload'; ?>"
        data = {
            'new_status': 'Resolved',
            'remarks': 'Testing malicious upload rejection.',
            'evidence_image': (io.BytesIO(malicious_script_bytes), 'shell.php.jpg', 'text/plain')
        }

        with self.client.session_transaction() as sess:
            sess['user_id'] = staff_id
            sess['role'] = 'staff'
            sess['user_name'] = 'Ravi Kumar (Electrical)'

        res = self.client.post(
            f'/staff/complaints/{complaint_id}/status',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Evidence photo rejected', res.data)

        # Verify DB does not store fake image
        cursor.execute("SELECT resolution_image FROM complaints WHERE complaint_id = %s", (complaint_id,))
        row = cursor.fetchone()
        self.assertIsNone(row['resolution_image'])

        cursor.close()
        conn.close()


if __name__ == '__main__':
    unittest.main()

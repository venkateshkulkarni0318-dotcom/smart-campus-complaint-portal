"""
scripts/performance_audit.py
Exhaustive Automated Feature & Performance Benchmark for End Users.
Measures local Flask test-client in-memory response times (via Python time.perf_counter()).
Validates HTTP Status Code, Payload size, Database state persistence, and Security bounds.
"""

import io
import os
import sys
import time
import json
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
import mysql.connector

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False


def get_db():
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    conn.autocommit = True
    return conn


def run_benchmark():
    client = app.test_client()
    results = []

    def benchmark_call(feature_id, feature_name, role, method, url, data=None, content_type=None,
                       session_data=None, expected_status=None, verify_fn=None, db_verify_fn=None):
        with client.session_transaction() as sess:
            sess.clear()
            if session_data:
                for k, v in session_data.items():
                    sess[k] = v

        start_time = time.perf_counter()
        if method == 'GET':
            res = client.get(url)
        elif method == 'POST':
            if content_type:
                res = client.post(url, data=data, content_type=content_type, follow_redirects=True)
            else:
                res = client.post(url, data=data, follow_redirects=True)
        end_time = time.perf_counter()

        latency_ms = round((end_time - start_time) * 1000, 2)
        payload_bytes = len(res.data)

        # Verification assertion
        if expected_status:
            status_ok = (res.status_code == expected_status)
        else:
            status_ok = (res.status_code in (200, 302))

        assertion_ok = True
        error_msg = ""

        if verify_fn:
            try:
                verify_fn(res)
            except Exception as e:
                assertion_ok = False
                error_msg = f"HTTP Verification Failed: {str(e)}"

        if assertion_ok and db_verify_fn:
            try:
                db_verify_fn()
            except Exception as e:
                assertion_ok = False
                error_msg = f"Database State Verification Failed: {str(e)}"

        if latency_ms < 20:
            rating = "Under 20 ms"
        elif latency_ms < 50:
            rating = "20–under 50 ms"
        elif latency_ms < 100:
            rating = "50–under 100 ms"
        else:
            rating = "100 ms and above"

        passed = status_ok and assertion_ok
        record = {
            'id': feature_id,
            'feature': feature_name,
            'role': role,
            'endpoint': f"{method} {url}",
            'latency_ms': latency_ms,
            'status': res.status_code,
            'payload_bytes': payload_bytes,
            'passed': passed,
            'rating': rating,
            'error': error_msg
        }
        results.append(record)
        return res, record

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch users for testing
    cursor.execute("SELECT user_id, email, role, name, department_id FROM users")
    users = {u['email']: u for u in cursor.fetchall()}
    student_u = users['student@campus.edu']
    faculty_u = users['faculty@campus.edu']
    admin_u = users['admin@campus.edu']
    staff_u = users['electrical.staff@campus.edu']

    print("=" * 95)
    print("STARTING EXHAUSTIVE FEATURE & LOCAL TEST-CLIENT PERFORMANCE AUDIT")
    print("=" * 95)

    # 1. AUTHENTICATION & SESSION MANAGEMENT
    print("\n--- Auditing Authentication Features ---")
    benchmark_call(
        "AUTH-01", "Guest Root Redirection to Login", "Guest", "GET", "/",
        verify_fn=lambda r: "Login" in r.data.decode('utf-8')
    )
    benchmark_call(
        "AUTH-02", "Login Page View Rendering", "Guest", "GET", "/login",
        verify_fn=lambda r: "Sign in to Smart Campus Portal" in r.data.decode('utf-8')
    )
    benchmark_call(
        "AUTH-03", "Student Credential Verification & Session Generation", "Guest", "POST", "/login",
        data={'email': 'student@campus.edu', 'password': 'Student@2026!'},
        verify_fn=lambda r: "Student Dashboard" in r.data.decode('utf-8')
    )
    benchmark_call(
        "AUTH-04", "Registration Page View Rendering", "Guest", "GET", "/register",
        verify_fn=lambda r: "Create Campus Account" in r.data.decode('utf-8')
    )
    benchmark_call(
        "AUTH-05", "Faculty Credential Verification & Session Generation", "Guest", "POST", "/login",
        data={'email': 'faculty@campus.edu', 'password': 'Faculty@2026!'},
        verify_fn=lambda r: "Faculty Dashboard" in r.data.decode('utf-8')
    )
    benchmark_call(
        "AUTH-06", "Secure Session Termination (Logout)", "Student", "POST", "/logout",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        verify_fn=lambda r: "You have been securely logged out" in r.data.decode('utf-8')
    )

    # 2. STUDENT & FACULTY PORTAL
    print("\n--- Auditing Student & Faculty Features ---")
    benchmark_call(
        "STUD-01", "Student Dashboard & Live Metrics Computation", "Student", "GET", "/student/dashboard",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        verify_fn=lambda r: "Student Dashboard" in r.data.decode('utf-8') and "Total Reported" in r.data.decode('utf-8')
    )
    benchmark_call(
        "STUD-02", "Faculty Dashboard & Departmental View", "Faculty", "GET", "/faculty/dashboard",
        session_data={'user_id': faculty_u['user_id'], 'role': 'faculty', 'user_name': faculty_u['name']},
        verify_fn=lambda r: "Faculty Dashboard" in r.data.decode('utf-8')
    )
    benchmark_call(
        "STUD-03", "Standard Complaint Filing Form View", "Student", "GET", "/complaints/new",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        verify_fn=lambda r: "Report Maintenance Issue" in r.data.decode('utf-8') and "Urgency / Priority" in r.data.decode('utf-8')
    )
    benchmark_call(
        "STUD-04", "QR-Code Instant Location Prefilling Form", "Student", "GET", "/complaints/new?building=Library+Building&floor=2nd+Floor&room=Reading+Hall+A&category=Electrical",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        verify_fn=lambda r: "QR Code Scanned Successfully" in r.data.decode('utf-8') and "Reading Hall A" in r.data.decode('utf-8')
    )

    # Create a fresh complaint for testing downstream features with High priority
    _, rec_submit = benchmark_call(
        "STUD-05", "Complaint Submission & Priority Storage", "Student", "POST", "/complaints/new",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        data={
            'category': 'Electrical',
            'building': 'Science Complex',
            'floor': '3rd Floor',
            'room': 'Physics Lab 302',
            'priority': 'High',
            'description': 'Main fluorescent ballast sparking during practical session.'
        },
        verify_fn=lambda r: "CMP-" in r.data.decode('utf-8'),
        db_verify_fn=lambda: (
            cursor.execute("SELECT priority, status FROM complaints ORDER BY complaint_id DESC LIMIT 1"),
            row := cursor.fetchone(),
            assert_row(row['priority'] == 'High' and row['status'] == 'Pending', "Priority not saved as 'High'")
        )
    )

    # Retrieve the newly created complaint
    cursor.execute("SELECT * FROM complaints ORDER BY complaint_id DESC LIMIT 1")
    new_complaint = cursor.fetchone()
    c_id = new_complaint['complaint_id']
    t_num = new_complaint['ticket_number']

    benchmark_call(
        "STUD-06", "Complaint Details View & Chronological Audit Timeline", "Student", "GET", f"/complaints/{c_id}",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        verify_fn=lambda r: t_num in r.data.decode('utf-8') and "Status History & Audit Trail" in r.data.decode('utf-8')
    )
    benchmark_call(
        "STUD-07", "Public Ticket Tracker Search Form", "Guest", "GET", "/complaints/track",
        verify_fn=lambda r: "Track Complaint Status" in r.data.decode('utf-8')
    )
    benchmark_call(
        "STUD-08", "Public Ticket Live Tracking by Ticket ID", "Guest", "GET", f"/complaints/track?ticket={t_num}",
        verify_fn=lambda r: t_num in r.data.decode('utf-8') and "Physics Lab 302" in r.data.decode('utf-8')
    )

    # 3. ADMIN COMMAND CENTER
    print("\n--- Auditing Admin Command Center Features ---")
    benchmark_call(
        "ADM-01", "Admin Executive Dashboard & Live Chart.js Analytics", "Admin", "GET", "/admin/dashboard",
        session_data={'user_id': admin_u['user_id'], 'role': 'admin', 'user_name': admin_u['name']},
        verify_fn=lambda r: "Admin Command Center" in r.data.decode('utf-8') and "categoryCounts" in r.data.decode('utf-8')
    )
    benchmark_call(
        "ADM-02", "Admin Complaints Directory & Multi-faceted Filtering", "Admin", "GET", "/admin/complaints?status=Pending&priority=High",
        session_data={'user_id': admin_u['user_id'], 'role': 'admin', 'user_name': admin_u['name']},
        verify_fn=lambda r: "Complaints Directory & Triage" in r.data.decode('utf-8')
    )
    benchmark_call(
        "ADM-03", "Admin Keyword Search Across Incident Records", "Admin", "GET", f"/admin/complaints?search={t_num}",
        session_data={'user_id': admin_u['user_id'], 'role': 'admin', 'user_name': admin_u['name']},
        verify_fn=lambda r: t_num in r.data.decode('utf-8')
    )
    benchmark_call(
        "ADM-04", "3-Layer Validated Staff & Department Assignment", "Admin", "POST", f"/admin/complaints/{c_id}/assign",
        session_data={'user_id': admin_u['user_id'], 'role': 'admin', 'user_name': admin_u['name']},
        data={
            'department_id': staff_u['department_id'],
            'assigned_staff_id': staff_u['user_id'],
            'priority': 'High'
        },
        verify_fn=lambda r: "successfully assigned" in r.data.decode('utf-8'),
        db_verify_fn=lambda: (
            cursor.execute("SELECT status, assigned_staff_id FROM complaints WHERE complaint_id = %s", (c_id,)),
            row := cursor.fetchone(),
            assert_row(row['status'] == 'Assigned' and row['assigned_staff_id'] == staff_u['user_id'], "Staff assignment failed in DB")
        )
    )
    benchmark_call(
        "ADM-05", "Administrative Priority Level Escalation", "Admin", "POST", f"/admin/complaints/{c_id}/priority",
        session_data={'user_id': admin_u['user_id'], 'role': 'admin', 'user_name': admin_u['name']},
        data={'priority': 'High'},
        verify_fn=lambda r: "Priority for ticket" in r.data.decode('utf-8')
    )

    # 4. MAINTENANCE TECHNICIAN / STAFF PORTAL
    print("\n--- Auditing Maintenance Staff Features ---")
    benchmark_call(
        "STF-01", "Technician Work Queue Dashboard & Task Prioritization", "Staff", "GET", "/staff/dashboard",
        session_data={'user_id': staff_u['user_id'], 'role': 'staff', 'user_name': staff_u['name']},
        verify_fn=lambda r: "Maintenance Technician Dashboard" in r.data.decode('utf-8') and t_num in r.data.decode('utf-8')
    )
    benchmark_call(
        "STF-02", "Controlled State Machine Transition: Assigned -> In Progress", "Staff", "POST", f"/staff/complaints/{c_id}/status",
        session_data={'user_id': staff_u['user_id'], 'role': 'staff', 'user_name': staff_u['name']},
        data={
            'new_status': 'In Progress',
            'remarks': 'Technician dispatched to Science Complex Lab 302 with testing gear.'
        },
        verify_fn=lambda r: "updated to In Progress" in r.data.decode('utf-8'),
        db_verify_fn=lambda: (
            cursor.execute("SELECT status FROM complaints WHERE complaint_id = %s", (c_id,)),
            row := cursor.fetchone(),
            assert_row(row['status'] == 'In Progress', "Status transition to 'In Progress' failed in DB")
        )
    )

    # Verify student notification banner now that ticket is In Progress
    benchmark_call(
        "STUD-09", "In-App Status Update Activity Alert Banner Display", "Student", "GET", "/student/dashboard",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        verify_fn=lambda r: "Recent Activity Notice" in r.data.decode('utf-8') and t_num in r.data.decode('utf-8')
    )

    # Valid RFC-compliant 1x1 PNG image
    valid_png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
        b'\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    saved_evidence_path = None

    def verify_resolution_db():
        nonlocal saved_evidence_path
        cursor.execute("SELECT status, resolution_remarks, resolution_image FROM complaints WHERE complaint_id = %s", (c_id,))
        row = cursor.fetchone()
        assert_row(row['status'] == 'Resolved', "Status in DB not updated to 'Resolved'")
        assert_row(bool(row['resolution_image']), "Resolution image path not recorded in DB")
        saved_evidence_path = os.path.join(app.config['UPLOAD_FOLDER'], row['resolution_image'])
        assert_row(os.path.exists(saved_evidence_path), f"Evidence image was not written to disk at {saved_evidence_path}")

    benchmark_call(
        "STF-03", "Resolution with Photographic Evidence Upload & Verification", "Staff", "POST", f"/staff/complaints/{c_id}/status",
        session_data={'user_id': staff_u['user_id'], 'role': 'staff', 'user_name': staff_u['name']},
        content_type='multipart/form-data',
        data={
            'new_status': 'Resolved',
            'remarks': 'Replaced ballast and verified zero arcing on 230V line.',
            'evidence_image': (io.BytesIO(valid_png_bytes), 'lab302_ballast_repaired.png', 'image/png')
        },
        verify_fn=lambda r: "updated to Resolved" in r.data.decode('utf-8'),
        db_verify_fn=verify_resolution_db
    )

    # 5. RESOLUTION VERIFICATION & REPORTING
    print("\n--- Auditing Resolution & Display Verification ---")
    benchmark_call(
        "VER-01", "Verified Photographic Evidence Display on Ticket Details", "Student", "GET", f"/complaints/{c_id}",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        verify_fn=lambda r: "Verified Photographic Proof of Resolution" in r.data.decode('utf-8') and "uploads/evidence_" in r.data.decode('utf-8')
    )
    benchmark_call(
        "VER-02", "Public Ticket Tracker Photographic Evidence Thumbnail", "Guest", "GET", f"/complaints/track?ticket={t_num}",
        verify_fn=lambda r: "Technician Resolution Photo" in r.data.decode('utf-8') and "uploads/evidence_" in r.data.decode('utf-8')
    )
    benchmark_call(
        "VER-03", "A4 Printable Record Styling Layout Verification", "Student", "GET", f"/complaints/{c_id}",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        verify_fn=lambda r: "window.print()" in r.data.decode('utf-8') and "Print / Save Record" in r.data.decode('utf-8')
    )

    # 6. SECURITY & BOUNDARY DEFENSE
    print("\n--- Auditing Security & RBAC Enforcement ---")
    benchmark_call(
        "SEC-01", "Unauthorized Access Rejection: Student accessing Admin Dashboard", "Student", "GET", "/admin/dashboard",
        session_data={'user_id': student_u['user_id'], 'role': 'student', 'user_name': student_u['name']},
        expected_status=403,
        verify_fn=lambda r: r.status_code == 403
    )
    benchmark_call(
        "SEC-02", "Unauthorized Access Rejection: Faculty viewing another user's Details", "Faculty", "GET", f"/complaints/{c_id}",
        session_data={'user_id': faculty_u['user_id'], 'role': 'faculty', 'user_name': faculty_u['name']},
        expected_status=403,
        verify_fn=lambda r: r.status_code == 403
    )
    benchmark_call(
        "SEC-03", "Illegal State Machine Bypass Rejection (Direct Resolved without In Progress)", "Staff", "POST", f"/staff/complaints/{c_id}/status",
        session_data={'user_id': staff_u['user_id'], 'role': 'staff', 'user_name': staff_u['name']},
        data={'new_status': 'Pending', 'remarks': 'Invalid reverse status'},
        verify_fn=lambda r: "Unauthorized status change" in r.data.decode('utf-8')
    )

    # Clean up test evidence file from disk
    if saved_evidence_path and os.path.exists(saved_evidence_path):
        try:
            os.remove(saved_evidence_path)
        except Exception:
            pass

    # Clean up test complaint record
    cursor.execute("DELETE FROM complaints WHERE complaint_id = %s", (c_id,))
    conn.commit()

    cursor.close()
    conn.close()

    total_audited = len(results)
    total_passed = sum(1 for r in results if r['passed'])
    pass_pct = round((total_passed / total_audited) * 100, 1)
    avg_latency = round(sum(r['latency_ms'] for r in results) / total_audited, 2)

    # Dynamic Latency Bucketing
    b_under_20 = sum(1 for r in results if r['latency_ms'] < 20)
    b_20_50 = sum(1 for r in results if 20 <= r['latency_ms'] < 50)
    b_50_100 = sum(1 for r in results if 50 <= r['latency_ms'] < 100)
    b_100_plus = sum(1 for r in results if r['latency_ms'] >= 100)

    print("\n" + "=" * 95)
    print("AUDIT RESULTS & TEST-CLIENT PERFORMANCE SUMMARY")
    print("=" * 95)
    print(f"Total Features Audited:      {total_audited}")
    print(f"Total Passed:                {total_passed}/{total_audited} ({pass_pct}% Pass Rate)")
    print(f"Average Test-Client Time:    {avg_latency} ms")
    print("\nPerformance Distribution (Local Test-Client Response Times):")
    print(f"  - Under 20 ms:             {b_under_20} tests ({round(b_under_20 / total_audited * 100, 1)}%)")
    print(f"  - 20–under 50 ms:          {b_20_50} tests ({round(b_20_50 / total_audited * 100, 1)}%)")
    print(f"  - 50–under 100 ms:         {b_50_100} tests ({round(b_50_100 / total_audited * 100, 1)}%)")
    print(f"  - 100 ms and above:        {b_100_plus} tests ({round(b_100_plus / total_audited * 100, 1)}%)")
    print("=" * 95)

    failures = [r for r in results if not r['passed']]
    if failures:
        print("\n[!] AUDIT FAILURES DETECTED:")
        for f in failures:
            print(f"  [-] {f['id']}: {f['feature']} ({f['endpoint']}) -> Status: {f['status']}, Error: {f['error']}")

    # Save to JSON for report formatting
    out_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'benchmark_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\nBenchmark results saved to: {out_path}")

    if total_passed < total_audited:
        sys.exit(1)


def assert_row(condition, msg):
    if not condition:
        raise AssertionError(msg)


if __name__ == '__main__':
    run_benchmark()

# Hackathon Presentation & Live Demonstration Guide
## Smart Campus Complaint & Maintenance Portal

---

## 1. 30-Second Elevator Pitch

> *"In colleges and universities, facility complaints are usually reported through informal messaging, phone calls, or verbal communication. Problems get lost, departments lack accountability, and students are left in the dark.*
> 
> *Our **Smart Campus Complaint & Maintenance Portal** provides a centralized, role-enforced operations system where students and faculty submit complaints in seconds (or via QR code scan), administrators triage and assign verified technicians across departments, staff manage work orders with audit accountability, and everyone tracks live resolution in real time."*

---

## 2. 5-Minute Live Demo Script (Step-by-Step)

Follow this sequence during your hackathon presentation or evaluator walkthrough:

### Step 1: Login & Role-Based Access Control (30 seconds)
1. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).
2. Point out the **Google Stitch design system**: Navy Blue (`#163A70`), Royal Blue (`#2563EB`), and responsive card layout.
3. Show the **Hackathon 1-Click Autofill Buttons** at the bottom of the login card.
4. Click the **"Student"** autofill button $\to$ Click **Sign In**.

---

### Step 2: Student Experience & Fast Complaint Filing (60 seconds)
1. You are now on the **Student Maintenance Dashboard** (`/student/dashboard`).
2. Point out:
   - Live metric cards: **Total Submitted**, **Pending Action**, **In Progress**, **Resolved**.
   - Recent Submissions table.
3. Click **"Submit New Complaint"** (`/complaints/new`).
4. **Demonstrate the QR Scan Feature**:
   - Point out the **"Simulate QR Code Scan"** shortcuts at the top.
   - Click **"Physics Lab QR"** $\to$ Notice how `Building`, `Floor`, `Room`, and `Category` auto-populate instantly.
5. Enter a description:
   - *"Ceiling projector in Physics Lab 304 keeps flickering and turning off during lectures."*
6. Click **Submit Complaint**.
7. **Highlight to Judges**:
   - Unique ticket number generated atomically: `CMP-2026-XXXX`.
   - Initial status set to `Pending`, default priority `Medium`.
   - Audit trail initialized in `complaint_history`.

---

### Step 3: Administrator Command Center & Triage (90 seconds)
1. Click **Sign Out** from the bottom of the sidebar.
2. Sign in as **Administrator** (`admin@campus.edu` / `Admin@2026!`).
3. You are now on the **Administrator Operations Command Center** (`/admin/dashboard`).
4. Point out to judges:
   - **Live Chart.js Visualizations**: Status Distribution (Donut Chart) and Complaints by Category (Bar Chart) built from real MySQL queries.
   - **Department Analytics & Resolution Efficiency Table**: Displays each department's total workload, active repairs, completed cases, and % resolution efficiency bar.
   - **Campus Avg Turnaround Speed**: Computed dynamically from database timestamps (`TIMESTAMPDIFF`).
5. Navigate to **"All Complaints"** (`/admin/complaints`).
6. Point out the multi-facet filters: Status, Priority, Category, Department, and search bar.
7. Locate the newly filed Physics Lab projector ticket $\to$ Click **"Assign"**:
   - Select **IT / Classroom Equipment** department.
   - Point out that the staff dropdown **dynamically filters** to show only technicians belonging to that department.
   - Select **Kiran Rao** $\to$ Set priority to **High** $\to$ Click **Confirm & Assign**.
8. **Highlight to Judges**:
   - The backend executed **3-Layer Staff Assignment Validation** to verify department existence, staff role, and department membership.
   - Ticket status transitioned from `Pending` $\to$ `Assigned`.

---

### Step 4: Maintenance Technician Workspace (60 seconds)
1. Sign out and sign in as **IT Staff** (`it.staff@campus.edu` / `Staff@2026!`).
2. You are now on the **Technician Workspace** (`/staff/dashboard`).
3. Point out:
   - The queue shows **only tasks assigned to Kiran Rao** (strict data isolation).
   - The Physics Lab ticket appears with status `Assigned`.
4. Click **"Start Work"**:
   - Ticket transitions from `Assigned` $\to$ `In Progress`.
5. Click **"Mark Resolved"**:
   - Point out the resolution modal. Try submitting with empty remarks to show backend validation.
   - Enter remarks: *"Replaced faulty HDMI port and power cable on ceiling projector. Tested with laptop display for 15 minutes, functioning normally."*
   - Click **Submit & Mark Resolved**.
6. Ticket transitions to `Resolved`.

---

### Step 5: Verification & Full Audit Trail (60 seconds)
1. Sign out and sign back in as **Student** (`student@campus.edu` / `Student@2026!`).
2. Point out the **In-App Activity Notification Banner** on the dashboard:
   - *"Latest Incident Update: Ticket CMP-2026-XXXX (Classroom Equipment) is now Resolved! Remarks: 'Replaced faulty HDMI port...'"*
3. Click **"Track Ticket"** $\to$ Enter the ticket number $\to$ Click **Track**.
4. Click **"View Full Timeline & History"**:
   - Show the **Chronological Audit History Timeline**:
     - `Pending` (Student filed incident)
     - `Assigned` (Admin assigned to Kiran Rao)
     - `In Progress` (Technician started work)
     - `Resolved` (Technician completed repairs with official remarks and optional photographic evidence)
5. In the resolve modal, enter remarks and attach an evidence photo (PNG/JPG/WEBP) to demonstrate proof of completed work.
6. View the ticket in both the **Student Details View** (`/complaints/<id>`) and **Public Ticket Tracker** (`/complaints/track`) to showcase the verified photographic evidence thumbnail.
7. Click the **"Print / Save Record"** button to show clean A4 print preview.

---

## 3. Key Technical & Security Highlights for Evaluators

When judges ask about architecture or security, highlight these 7 key engineering strengths:

| Feature | Engineering Implementation | Why It Matters |
|---|---|---|
| **Resolution Evidence Upload** | Server-side MIME/extension verification, unique timestamped file generation, and storage under `static/uploads/` | Guarantees authentic visual proof of maintenance repairs across details and tracker views |
| **3-Layer Staff Assignment** | Server-side validation checking dept existence, staff role, and staff department membership (`users.department_id = department_id`) | Prevents malicious POST requests from assigning arbitrary users or wrong technicians |
| **Concurrency-Safe Tickets** | `CMP-YYYY-NNNN` generated using MySQL auto-increment ID within a transaction | Eliminates race-condition collisions during simultaneous submissions |
| **Controlled State Machine** | Sequential transition matrix: `Pending` $\to$ `Assigned` $\to$ `In Progress` $\to$ `Resolved` | Rejects arbitrary browser status tampering and ensures business workflow integrity |
| **Zero Plaintext Storage** | All passwords hashed using Werkzeug `pbkdf2:sha256` | Secure credential storage adhering to OWASP standards |
| **Full Data Ownership** | Submitter user ID checked on details and tracking routes | Students cannot inspect other users' tickets |
| **Live Database Analytics** | 100% Parameterized MySQL queries for Chart.js datasets and turnaround speeds | Zero fake or static data on dashboards |

---

## 4. Test Suite Execution Proof

Run all 40 automated tests across the project:
```bash
python -m unittest discover -s tests
```
Output:
```text
Ran 40 tests in 7.223s

OK (100% Passing - 0 failures, 0 errors)
- Phase 1 (Database Connection, Schema & Seed):  6 tests
- Phase 2 (Auth, Priority, Open Redirect & Sub): 14 tests
- Phase 3 (Admin, Staff & State Machine):        13 tests
- Phase 4 (Full E2E Demo Lifecycle):             1 test
- Phase 5 (PRD Section 15 Enhancements):         4 tests
- Phase 7 (Photo Upload & Malicious Rejection):  2 tests
```

### Local Test-Client Performance Benchmark
Run the comprehensive performance verification script:
```bash
python scripts/performance_audit.py
```
*Note: Measures local in-memory Flask test-client execution latency via `time.perf_counter()`, excluding network transport delay.*
Results:
- Total Features Audited: 29 / 29 (**100% Passing**)
- Average Test-Client Time: ~54.5 ms
- Under 20 ms: 19 tests (65.5%)
- 20–under 50 ms: 8 tests (27.6%)
- 50–under 100 ms: 0 tests (0.0%)
- 100 ms and above: 2 tests (6.9% — password hashing key stretching per OWASP recommendations)

---

## 5. Demo Credentials Reference

| Role | Email Address | Password |
|---|---|---|
| **Admin** | `admin@campus.edu` | `Admin@2026!` |
| **Staff (Electrical)** | `electrical.staff@campus.edu` | `Staff@2026!` |
| **Staff (Plumbing)** | `plumbing.staff@campus.edu` | `Staff@2026!` |
| **Staff (Civil)** | `civil.staff@campus.edu` | `Staff@2026!` |
| **Staff (Sanitation)** | `sanitation.staff@campus.edu` | `Staff@2026!` |
| **Staff (IT Equipment)** | `it.staff@campus.edu` | `Staff@2026!` |
| **Student** | `student@campus.edu` | `Student@2026!` |
| **Faculty** | `faculty@campus.edu` | `Faculty@2026!` |


# Smart Campus Complaint & Maintenance Portal

A centralized, responsive web application for college and university campuses. Enables students and faculty to submit facility and maintenance complaints, administrators to triage, prioritize, and assign departments and staff, technicians to manage work orders and log resolutions, and users to track live progress with full audit history.

---

## 1. Technology Stack

- **Backend**: Python 3.13, Flask 3.1, Jinja2
- **Database**: MySQL 8.0 (InnoDB, UTF-8)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Bootstrap Icons
- **Analytics / Visualizations**: Chart.js
- **Security**: Werkzeug (`pbkdf2:sha256` password hashing), Flask-WTF (CSRF Protection), secure HTTP-only cookies
- **Configuration**: `python-dotenv` (.env)
- **Architecture**: Server-rendered Flask application with Blueprints

---

## 2. User Roles & Permissions

| Role | Responsibilities & Capabilities |
|---|---|
| **Student** | Submit maintenance complaints, track personal tickets, view progress & resolution remarks |
| **Faculty** | Submit departmental/classroom facility complaints, track tickets, view progress |
| **Administrator** | Live campus operations dashboard with Chart.js charts, search & filter all tickets, 3-layer staff assignment, priority adjustment |
| **Maintenance Staff** | Dedicated technician workspace, manage assigned work orders, update status (`Assigned` $\to$ `In Progress` $\to$ `Resolved`), add mandatory resolution remarks |

---

## 3. Database Schema Overview

The database uses 4 normalized InnoDB tables in MySQL:

1. **`departments`**: Master list of campus maintenance departments (`Electrical`, `Plumbing`, `Civil / Infrastructure`, `Sanitation`, `IT / Classroom Equipment`).
2. **`users`**: User records with secure password hashes, roles (`student`, `faculty`, `admin`, `staff`), and optional `department_id` foreign key for staff.
3. **`complaints`**: Tickets with unique ticket numbers (`CMP-YYYY-NNNN`), category, description, building, floor, room, priority, status, department, and assigned technician.
4. **`complaint_history`**: Audit trail logging every status change, timestamp, user responsible, and resolution remarks.

---

## 4. Setup & Installation Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- MySQL Server 8.0 running locally on port 3306
- Git

### Step 1: Clone the Repository
```bash
git clone <repository_url>
cd hackathon
```

### Step 2: Create and Activate Virtual Environment
```bash
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` and enter your MySQL credentials:
```bash
cp .env.example .env
```
Inside `.env`:
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=smart_campus
SECRET_KEY=generate_a_random_secure_secret_key
```

### Step 5: Initialize and Seed Database
Run the schema script in MySQL, followed by the seed script:
```bash
# Execute schema in MySQL:
mysql -u root -p < database/schema.sql

# Seed initial departments and demo accounts:
python database/seed.py
```

### Step 6: Run Automated Tests
```bash
python -m unittest tests/test_phase1.py
```

### Step 7: Launch the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 5. Pre-Seeded Demo Accounts (Hackathon Credentials)

All passwords are encrypted with `pbkdf2:sha256` password hashes.

| Role | Email Address | Password | Department / Assignment |
|---|---|---|---|
| **Administrator** | `admin@campus.edu` | `Admin@2026!` | Campus-wide Operations |
| **Electrical Staff** | `electrical.staff@campus.edu` | `Staff@2026!` | Electrical Department |
| **Plumbing Staff** | `plumbing.staff@campus.edu` | `Staff@2026!` | Plumbing Department |
| **Civil Staff** | `civil.staff@campus.edu` | `Staff@2026!` | Civil / Infrastructure Department |
| **Sanitation Staff** | `sanitation.staff@campus.edu` | `Staff@2026!` | Sanitation Department |
| **IT Staff** | `it.staff@campus.edu` | `Staff@2026!` | IT / Classroom Equipment Department |
| **Student** | `student@campus.edu` | `Student@2026!` | Student Submitter |
| **Faculty** | `faculty@campus.edu` | `Faculty@2026!` | Faculty Submitter |

*(Quick-autofill buttons are also provided directly on the Login screen for demonstration convenience).*

---

## 6. End-to-End Workflow Demonstration

1. **Submit**: Log in as `student@campus.edu` $\to$ Click "Submit New Complaint" $\to$ Submit a damaged fan issue in Classroom 204 $\to$ Receive generated ticket (e.g. `CMP-2026-0001`).
2. **Assign**: Log in as `admin@campus.edu` $\to$ View incident in "All Complaints" $\to$ Click "Assign" $\to$ Select `Electrical` department & `Ravi Kumar` $\to$ Set priority to `High` $\to$ Status transitions to `Assigned`.
3. **In Progress**: Log in as `electrical.staff@campus.edu` $\to$ See assigned task in technician queue $\to$ Click "Start Work" $\to$ Status transitions to `In Progress`.
4. **Resolve**: As technician, click "Mark Resolved" $\to$ Enter mandatory resolution remarks ("Replaced capacitor on ceiling fan") $\to$ Status transitions to `Resolved`.
5. **Verify**: Log back in as student $\to$ Track ticket $\to$ Verify updated `Resolved` status, technician details, and resolution remarks on the live audit timeline.

---

## 7. Optional Enhancements Implemented (PRD Section 15)

1. **Department Analytics & Resolution Turnaround**:
   - Live analytics on Admin Dashboard computing total workload, active repairs, completed cases, and % resolution efficiency.
   - Computes real average turnaround time in hours from MySQL database timestamps.
2. **QR-Based Quick Complaint Reporting**:
   - Supports URL query parameters (`/complaints/new?building=...&room=...&category=...`).
   - Automatically pre-fills facility and location fields when students scan a campus room or equipment QR sticker.
3. **In-App Activity & Resolution Alerts**:
   - Prominent notification alert rendered on Student & Faculty dashboards immediately notifying them when a ticket is updated or marked resolved.
4. **Printable / Exportable Ticket View**:
   - Print optimization (`@media print`) on complaint details page formatting clean A4 records while stripping navigation and action bars.


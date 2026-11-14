"""
database/seed.py
Seeds departments and pre-configured demo accounts with securely hashed passwords.
Passes all passwords through werkzeug.security.generate_password_hash.
"""

import os
import sys
from dotenv import load_dotenv
import mysql.connector
from werkzeug.security import generate_password_hash

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'smart_campus')


def seed_database():
    print(f"Connecting to MySQL server at {DB_HOST}:{DB_PORT} as '{DB_USER}'...")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        sys.exit(1)

    cursor = conn.cursor(dictionary=True)

    # 1. Seed Departments
    departments = [
        'Electrical',
        'Plumbing',
        'Civil / Infrastructure',
        'Sanitation',
        'IT / Classroom Equipment'
    ]

    print("\n--- Seeding Departments ---")
    dept_map = {}
    for dept_name in departments:
        cursor.execute(
            "INSERT INTO departments (department_name) VALUES (%s) "
            "ON DUPLICATE KEY UPDATE department_id=LAST_INSERT_ID(department_id)",
            (dept_name,)
        )
        conn.commit()
        # Fetch the id
        cursor.execute("SELECT department_id FROM departments WHERE department_name = %s", (dept_name,))
        row = cursor.fetchone()
        dept_map[dept_name] = row['department_id']
        print(f"  [+] Department: {dept_name} (ID: {dept_map[dept_name]})")

    # 2. Seed Demo Accounts
    # Passwords hashed with werkzeug pbkdf2:sha256
    users_to_seed = [
        # Admin
        {
            'name': 'Campus Administrator',
            'email': 'admin@campus.edu',
            'password': 'Admin@2026!',
            'role': 'admin',
            'dept_name': None
        },
        # Staff (one for each department)
        {
            'name': 'Ravi Kumar (Electrical)',
            'email': 'electrical.staff@campus.edu',
            'password': 'Staff@2026!',
            'role': 'staff',
            'dept_name': 'Electrical'
        },
        {
            'name': 'Priya Singh (Plumbing)',
            'email': 'plumbing.staff@campus.edu',
            'password': 'Staff@2026!',
            'role': 'staff',
            'dept_name': 'Plumbing'
        },
        {
            'name': 'Arjun Mehta (Civil)',
            'email': 'civil.staff@campus.edu',
            'password': 'Staff@2026!',
            'role': 'staff',
            'dept_name': 'Civil / Infrastructure'
        },
        {
            'name': 'Sunita Patel (Sanitation)',
            'email': 'sanitation.staff@campus.edu',
            'password': 'Staff@2026!',
            'role': 'staff',
            'dept_name': 'Sanitation'
        },
        {
            'name': 'Kiran Rao (IT Equipment)',
            'email': 'it.staff@campus.edu',
            'password': 'Staff@2026!',
            'role': 'staff',
            'dept_name': 'IT / Classroom Equipment'
        },
        # Demo Student
        {
            'name': 'Aditya Sharma',
            'email': 'student@campus.edu',
            'password': 'Student@2026!',
            'role': 'student',
            'dept_name': None
        },
        # Demo Faculty
        {
            'name': 'Dr. Meera Nambiar',
            'email': 'faculty@campus.edu',
            'password': 'Faculty@2026!',
            'role': 'faculty',
            'dept_name': None
        }
    ]

    print("\n--- Seeding Demo Accounts ---")
    for u in users_to_seed:
        dept_id = dept_map.get(u['dept_name']) if u['dept_name'] else None
        pw_hash = generate_password_hash(u['password'], method='pbkdf2:sha256')

        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (u['email'],))
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE users SET name=%s, password_hash=%s, role=%s, department_id=%s WHERE user_id=%s",
                (u['name'], pw_hash, u['role'], dept_id, existing['user_id'])
            )
            print(f"  [*] Updated existing user: {u['email']} [{u['role']}]")
        else:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role, department_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (u['name'], u['email'], pw_hash, u['role'], dept_id)
            )
            print(f"  [+] Created user: {u['email']} [{u['role']}]")
        conn.commit()

    cursor.close()
    conn.close()
    print("\n[SUCCESS] Database seeded successfully!")


if __name__ == '__main__':
    seed_database()

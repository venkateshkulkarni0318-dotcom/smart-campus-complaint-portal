-- ============================================================
-- SMART CAMPUS COMPLAINT & MAINTENANCE PORTAL
-- Database Schema: database/schema.sql (Validated v2.0)
-- Engine: InnoDB, Charset: utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS smart_campus
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_campus;

-- ------------------------------------------------------------
-- 1. Departments Table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
  department_id   INT AUTO_INCREMENT PRIMARY KEY,
  department_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 2. Users Table
-- Supports roles: student, faculty, admin, staff.
-- Staff accounts are linked to their respective department.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  user_id       INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(100)  NOT NULL,
  email         VARCHAR(150)  NOT NULL UNIQUE,
  password_hash VARCHAR(255)  NOT NULL,
  role          ENUM('student','faculty','admin','staff') NOT NULL DEFAULT 'student',
  department_id INT           DEFAULT NULL,
  created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_user_dept
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
    ON DELETE SET NULL,
  INDEX idx_email  (email),
  INDEX idx_role   (role),
  INDEX idx_u_dept (department_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 3. Complaints Table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS complaints (
  complaint_id        INT AUTO_INCREMENT PRIMARY KEY,
  ticket_number       VARCHAR(20)   UNIQUE DEFAULT NULL,
  user_id             INT           NOT NULL,
  category            ENUM('Electrical','Plumbing','Infrastructure',
                           'Sanitation','Classroom Equipment','Other') NOT NULL,
  description         TEXT          NOT NULL,
  building            VARCHAR(100)  NOT NULL,
  floor               VARCHAR(20)   DEFAULT NULL,
  room                VARCHAR(50)   NOT NULL,
  priority            ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
  status              ENUM('Pending','Assigned','In Progress','Resolved')
                      NOT NULL DEFAULT 'Pending',
  department_id       INT           DEFAULT NULL,
  assigned_staff_id   INT           DEFAULT NULL,
  resolution_remarks  TEXT          DEFAULT NULL,
  created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
                      ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_complaint_user
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_complaint_dept
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
    ON DELETE SET NULL,
  CONSTRAINT fk_complaint_staff
    FOREIGN KEY (assigned_staff_id) REFERENCES users(user_id)
    ON DELETE SET NULL,
  INDEX idx_ticket  (ticket_number),
  INDEX idx_c_user  (user_id),
  INDEX idx_status  (status),
  INDEX idx_c_dept  (department_id),
  INDEX idx_staff   (assigned_staff_id),
  INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 4. Complaint History Table (Audit Trail)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS complaint_history (
  history_id   INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT         NOT NULL,
  old_status   VARCHAR(20) DEFAULT NULL,
  new_status   VARCHAR(20) NOT NULL,
  updated_by   INT         NOT NULL,
  remarks      TEXT        DEFAULT NULL,
  created_at   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_hist_complaint
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_hist_user
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_hist_complaint (complaint_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


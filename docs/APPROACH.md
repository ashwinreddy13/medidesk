# Project Approach & Architecture — Build Secure 24

**Team ID:** 72  
**Project Name:** MediDesk — Secure Clinic & Appointment Management  
**Team Size:** 4 Members  
**Primary Track / Domain:** HealthTech (PS-04)  
**Team Repository:** https://github.com/ashwinreddy13/medidesk  

---

## 1. Problem Understanding, Scope & Threat Model

### 1.1 Problem Statement & Real-World Motivation
MediDesk addresses the critical vulnerability surface present in digital outpatient clinical management systems: unauthenticated access to electronic health records (EHR), appointment tampering, doctor-patient schedule concurrency collision (double bookings), privilege escalation, and lack of non-repudiation auditability. The platform provides a zero-trust, role-governed outpatient management system strictly using synthetic demographic and clinical data.

### 1.2 Target Users & Personas
- **Patient:** Alex Johnson (and registered synthetic patients) — Books appointments, inspects available doctor schedules dynamically, views consultation history, accesses verified dummy clinical records, and checks privacy access logs in their personal Privacy Center.
- **Doctor:** Dr. Emily Stone, Dr. Alex Demo, Dr. Sarah Chen, Dr. Marcus Vance — Manages consultation queues, reviews patient history strictly under established care relationships, confirms or cancels appointments, and authors signed clinical encounter notes and prescriptions.
- **Administrator:** Hospital System Admin — Monitors overall clinic metrics, manages user account states, audits system health in the Security Center, and validates tamper-evident SHA-256 cryptographic audit hash chains.

### 1.3 Threat Model & Attack Surface
- **Critical Assets:** Patient EHR records, consultation histories, appointment slot reservations, session tokens, audit trail integrity.
- **Potential Attack Vectors:**
  - Insecure Direct Object References (IDOR): Accessing other patients' medical records by manipulating record or appointment IDs in the URL.
  - Race conditions & double-booking: Two users reserving the exact same doctor slot simultaneously.
  - Privilege Escalation: Patients or doctors accessing administrative metrics or doctor-exclusive endpoints.
  - Audit Trail Tampering: Malicious modification or deletion of sensitive database activity logs.
- **OWASP Top 10 Mitigations:**
  - Strict server-side Role-Based Access Control (RBAC) via centralized python decorators (`@roles_required`, `@login_required`).
  - Strict Anti-IDOR object-level ownership validation (`verify_patient_appointment_ownership`, `verify_patient_record_access`, `verify_doctor_appointment_ownership`).
  - Partial unique database indexing on `(doctor_id, appointment_date, appointment_time)` for active appointment states.
  - SHA-256 cryptographic hash-chained audit logging ensuring mathematical tamper evidence.
  - Defense-in-depth HTTP security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).

---

## 2. Technical Architecture & Secure System Design

### 2.1 High-Level Architecture Overview
MediDesk is engineered using a modular multi-tier architecture:
- **Presentation Layer:** Semantic HTML5 templates styled with modern design tokens, interactive micro-interactions, responsive CSS grid/flexbox layouts, accessible color contrasts, and vanilla JS controllers for dynamic slot checking and the floating AI Assistant.
- **Application & Route Layer:** Modular Flask blueprints (`auth`, `patient`, `doctor`, `admin`, `assistant`, `privacy`) ensuring strict separation of concerns.
- **Security Middleware & Guards:** Centralized RBAC, rate-limiting brute-force lockout, session isolation, and audit emission hooks.
- **Service Layer:** Encapsulated business logic (`appointments.py`, `medical_records.py`, `scheduling.py`, `users.py`).
- **Data Persistence Layer:** SQLite engine with foreign key enforcement and row factory abstraction (`database/db.py`).

### 2.2 Technology Stack Rationale
- **Backend:** Python 3 & Flask — Minimal overhead, high transparency, robust cryptographic libraries, and native modular blueprint architecture.
- **Persistence:** SQLite — Zero external dependency friction, deterministic atomic transactions, and relational schema integrity.
- **Frontend:** Vanilla CSS & HTML5 — Instantaneous loading, zero third-party script vulnerabilities, fully accessible UI tokens.
- **Security / Hashing:** Werkzeug PBKDF2-SHA256 password hashing & hashlib SHA-256 chain validation.

---

## 3. Implementation Milestones & 24-Hour Timeline

| Milestone / Phase | Time Window | Key Objectives & Deliverables | Security Verification | Status |
|---|---|---|---|---|
| **Phase 1: Foundation & Setup** | 0h – 4h | Onboarding compliance, schema design, synthetic data seeding | Zero-secret leaks, DB integrity | `Completed` |
| **Phase 2: Core Domain & Auth** | 4h – 12h | RBAC authentication, session protection, doctor/patient portals | Brute-force throttling & IDOR tests | `Completed` |
| **Phase 3: Scheduling & EHR** | 12h – 18h | Conflict-free appointment finder, record hashing, timeline | Concurrency tests & hash verification | `Completed` |
| **Phase 4: Security Center & AI** | 18h – 24h | SHA-256 audit chain verifier, MediDesk AI Navigator, Privacy Center | End-to-end integration & freeze | `Completed` |

---

## 4. Architecture Decision Records (ADRs)

### ADR-001: Strict Anti-IDOR Object Validation at Service Boundaries
- **Status:** Accepted
- **Context:** HealthTech systems frequently suffer from IDOR vulnerabilities where authenticated users change URL identifiers to inspect records of other patients.
- **Decision:** Every endpoint accessing an appointment or record invokes explicit ownership checks verifying that the entity belongs either to the requesting patient or the assigned physician.
- **Security Impact:** Eliminates vertical and horizontal privilege escalation on sensitive EHR assets.

### ADR-002: Cryptographic Audit Hash Chaining (Blockchain-like Ledger)
- **Status:** Accepted
- **Context:** Audit logs must be tamper-evident so unauthorized database alterations can be mathematically proven.
- **Decision:** Each audit log entry calculates `current_hash = SHA256(prev_hash + user_id + action + resource_type + resource_id + result + details)`. The Admin portal provides an automated one-click integrity verifier.
- **Security Impact:** Guarantees non-repudiation and immediate detection of unauthorized log modifications.

---

## 5. Testing & Security Verification Record
- **Smoke Tests:** Complete test coverage across Home (`/`), Authentication (`/login`, `/register`, `/demo-login`), Patient Dashboard, Doctor Dashboard, and Admin Security Center.
- **HTTP Status Verification:** Verified 200 OK responses, 302 redirects on authorization gates, and 403 on RBAC violation.
- **Live Local Deployment URL:** `http://127.0.0.1:5000`

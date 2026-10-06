# Deployment Documentation — Build Secure 24

## Overview

This directory contains deployment configuration and operational deployment records for **MediDesk — Secure Clinic & Appointment Management**.

---

## Live Deployment Reference

- **Live Application URL:** `http://127.0.0.1:5000` (Local) / Vercel Serverless Function
- **Hosting Platform:** Local Flask Server / Production-Ready WSGI / Vercel Serverless Python
- **Access Credentials (Synthetic Demo Accounts for Evaluators):**
  - **Patient Demo:** `patient@example.com` / `Patient@Secure2026!` (or one-click demo login on landing page)
  - **Doctor Demo:** `doctor@medidesk.com` / `Doctor@Secure2026!` (or one-click demo login on landing page)
  - **Admin Demo:** `admin@medidesk.com` / `Admin@Secure2026!` (or one-click demo login on landing page)

---

## Required Environment Variables

| Variable Name | Description | Required | Default |
|---------------|-------------|----------|---------|
| `FLASK_APP` | Application entry file | No | `src/app.py` |
| `SECRET_KEY` | Cryptographic session encryption key | Optional in dev | `medidesk-dev-secret-key-change-in-production-2026-vbit` |
| `DATABASE_PATH` | Path to persistent SQLite database | No | `src/database/medidesk.db` (falls back to `/tmp/medidesk.db` on Vercel) |
| `SESSION_COOKIE_SECURE` | Force secure HTTPS cookie flags | No | `False` (set `True` behind TLS) |
| `PORT` | Listening server port | No | `5000` |

---

## Deployment Options

### Option 1: Local / Virtual Machine / Docker
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch the application server:**
   ```bash
   python run.py
   # OR
   python src/app.py
   ```
3. Open `http://127.0.0.1:5000`.

### Option 2: Vercel Serverless Deployment
- Configured with `vercel.json` routing all requests to `api/index.py`.
- Root `requirements.txt` installs dependencies automatically during build.
- Serverless read-only filesystem is handled dynamically with automatic fallback to `/tmp/medidesk.db`.

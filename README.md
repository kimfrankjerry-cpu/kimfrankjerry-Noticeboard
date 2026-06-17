# Smart Kiosk CMS — Backend Server (PRJ017)

> **The central control room for a digital signage network.**  
> A Flask-based Content Management System that manages multimedia notices, schedules display windows, and serves a REST API to a remote Raspberry Pi running a Kivy-powered kiosk frontend.

---

## Table of Contents

1. [Project Description](#1-project-description)
2. [Key Features](#2-key-features)
3. [Prerequisites](#3-prerequisites)
4. [Installation & Setup](#4-installation--setup)
5. [Environment Variables](#5-environment-variables)
6. [Running the Application](#6-running-the-application)
7. [API Documentation](#7-api-documentation)
8. [Project Structure](#8-project-structure)
9. [Database Schema](#9-database-schema)
10. [Admin Web Interface Routes (Reference)](#10-admin-web-interface-routes-reference)

---

## 1. Project Description

The **Smart Kiosk CMS** is the server-side backbone of a two-tier digital notice board system. Administrators interact with a web-based dashboard (served by this Flask app) to upload, schedule, and manage multimedia content (images and videos). A Raspberry Pi client running a Kivy display application periodically polls this server's REST API to synchronise its local media library and display the correct notices in real time.

> **Note:** This repository contains *only* the Flask backend server. The Raspberry Pi Kivy display frontend is maintained in a separate repository.

The system uses an **Application Factory** pattern (`create_app()` in `app.py`), making the codebase easy to test and configure for different deployment environments.

---

## 2. Key Features

| Feature | Details |
|---|---|
| 🔐 **Secure Admin Authentication** | Session-based login powered by **Flask-Login** and **Flask-Bcrypt**. Passwords are always stored as bcrypt hashes — never in plain text. |
| 👥 **Role-Based Access Control** | Two roles: `superadmin` (full access, user management) and `editor` (content management only). |
| 🖼️ **Media Upload & Processing** | Accepts PNG, JPG/JPEG, and MP4 files up to 50 MB. Uploaded images are automatically resized to a maximum of **1920×1080** using **Pillow** (`Image.thumbnail` with `LANCZOS` resampling) to optimise storage on the Pi's SD card. |
| 📅 **Notice Scheduling** | Every notice has a `valid_from` / `valid_until` window. The API only returns notices that are currently within their active window. |
| 🗃️ **SQLite Database** | Lightweight, file-based **SQLite** database managed via **Flask-SQLAlchemy**. No separate database server required. |
| 🔌 **REST API for Kiosk Sync** | Two protected API endpoints (bearer-token authenticated) allow the Raspberry Pi sync agent to fetch the active notice manifest and download media files. |
| 📋 **Audit Logging** | All admin actions (uploads, edits, deletions, user management) are recorded in an `audit_logs` table and displayed on the system status page. |
| 🖥️ **System Status Dashboard** | Real-time view of server uptime, media file count, total storage used, last Pi sync timestamp, and recent audit log entries. |
| 🔑 **Password Reset Flow** | Superadmins can generate temporary passwords for other users. The system forces a mandatory password change on the user's next login. |

---

## 3. Prerequisites

Ensure the following software is installed on your system before proceeding:

- **Python 3.8+** — [Download from python.org](https://www.python.org/downloads/)
- **pip** — Python package installer (bundled with Python 3.4+)
- **Git** — For cloning the repository

> **Note:** This project is developed and tested for deployment on both Windows (development) and Raspberry Pi OS / Linux (production).

---

## 4. Installation & Setup

### Step 1 — Clone the Repository

```bash
git clone https://github.com/kimfrankjerry/kimfrankjerry-Noticeboard.git
cd kimfrankjerry-Noticeboard
```

### Step 2 — Create a Virtual Environment

It is strongly recommended to use a virtual environment to isolate project dependencies.

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux / Raspberry Pi OS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Your prompt should now show `(venv)` to confirm the environment is active.

### Step 3 — Install Dependencies

Since a `requirements.txt` may not yet be present, you can install the core packages directly:

```bash
pip install Flask Flask-SQLAlchemy Flask-Login Flask-Bcrypt Pillow python-dotenv
```

Core packages installed include:

| Package | Role |
|---|---|
| `Flask` | Core web framework |
| `Flask-SQLAlchemy` | ORM for database access |
| `Flask-Login` | Session-based user authentication |
| `Flask-Bcrypt` | Bcrypt password hashing |
| `Pillow` | Image processing and auto-resizing |
| `Werkzeug` | Secure filename sanitisation (`secure_filename`) |

---

## 5. Environment Variables

The application reads sensitive configuration values from environment variables, falling back to safe defaults for development. For production, **always** override these defaults.

| Variable | Description | Default (Dev Only) |
|---|---|---|
| `SECRET_KEY` | Flask session signing key. **Must be changed** in production to a long, random string. | `change-this-in-production` |
| `API_TOKEN` | Bearer token the Raspberry Pi sync agent includes in every API request header. **Must be changed** in production. | `3dbebc76-46e7-4bdb-a619-e0179124986d` |

### Setting Environment Variables

**Option A — Shell (temporary, current session only):**

```bash
# Linux / macOS / Raspberry Pi
export SECRET_KEY="your-long-random-secret-key"
export API_TOKEN="your-long-random-api-token"
```

```powershell
# Windows PowerShell
$env:SECRET_KEY = "your-long-random-secret-key"
$env:API_TOKEN  = "your-long-random-api-token"
```

**Option B — `.env` file (recommended for development):**

Create a `.env` file in the project root (it is listed in `.gitignore` and will not be committed):

```dotenv
SECRET_KEY=your-long-random-secret-key-here
API_TOKEN=your-long-random-api-token-here
```

To load this file automatically when running `python app.py`, ensure `python-dotenv` is installed and add the following two lines at the very top of `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```
Alternatively, you can start the server using `flask run` (which loads `.env` files automatically) instead of `python app.py`.

> ⚠️ **Security Warning:** Never commit real `SECRET_KEY` or `API_TOKEN` values to version control. The `.gitignore` already excludes `.env`.

---

## 6. Running the Application

### Initialize the Database (First Run)

The database is automatically created and seeded on the first startup — no manual migration step is required. Simply run the app:

```bash
python app.py
```

On the first run, the database tables are created and a default superadmin account is seeded automatically:

- **Username:** `admin`
- **Password:** `admin1234`
- **Role:** `superadmin`

> ⚠️ **ACTION REQUIRED:** Navigate to **Admin Panel → Users** and change this password immediately after your first login! A prominent warning will also be printed in your terminal.

### Start the Development Server

```bash
python app.py
```

The server starts on `http://0.0.0.0:5000`, making it accessible from any device on the local network — including the Raspberry Pi client.

- **CMS Web Interface:** `http://<server-ip>:5000/`
- **API (for Pi):** `http://<server-ip>:5000/api/manifest`

> 💡 **Production Note:** For production deployment, replace `app.run(debug=True)` with a WSGI server such as **Gunicorn**: `gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"`. Set `debug=False`.

---

## 7. API Documentation

The API is consumed exclusively by the **Raspberry Pi sync agent**. All API endpoints require a valid **Bearer Token** in the `Authorization` HTTP header.

**Request Header (required on all API calls):**
```
Authorization: Bearer <API_TOKEN>
```

### Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/manifest` | Bearer Token | Returns a JSON array of all currently active, published notices. A notice is active when `NOW` falls within its `valid_from`–`valid_until` window. Results are ordered by `priority` descending. |
| `GET` | `/api/media/<filename>` | Bearer Token | Streams the raw media file (image or video) from the server's `media/` folder to the Pi for local caching. |

### `GET /api/manifest` — Response Schema

**Success (200 OK):**
```json
[
  {
    "id": 1,
    "title": "Exam Timetable",
    "filename": "exam_timetable.jpg",
    "content_type": "image/jpeg",
    "duration": 15,
    "priority": 5,
    "checksum": "d41d8cd98f00b204e9800998ecf8427e"
  },
  {
    "id": 2,
    "title": "Staff Meeting Notice",
    "filename": "staff_meeting.mp4",
    "content_type": "video/mp4",
    "duration": 30,
    "priority": 3,
    "checksum": "9e107d9d372bb6826bd81d3542a419d6"
  }
]
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique notice identifier |
| `title` | string | Display title of the notice |
| `filename` | string | Filename used to construct the `/api/media/<filename>` download URL |
| `content_type` | string | MIME type (e.g. `image/jpeg`, `video/mp4`) |
| `duration` | integer | Time in **seconds** to display this notice on screen |
| `priority` | integer | Display priority; higher number = shown first in the playlist |
| `checksum` | string | MD5 hex digest of the media file — used by the Pi to verify download integrity |

**Error Responses:**

| Code | Cause |
|---|---|
| `401 Unauthorized` | Missing, malformed, or invalid `Authorization` header / token |
| `500 Internal Server Error` | Unexpected server-side error |

### `GET /api/media/<filename>` — Response

Streams the raw binary file. The Pi sync agent saves it to its local cache directory.

**Example request (Python `requests`):**
```python
import requests

headers = {"Authorization": "Bearer your-api-token-here"}
base_url = "http://192.168.1.100:5000"

# 1. Fetch the manifest
manifest = requests.get(f"{base_url}/api/manifest", headers=headers).json()

# 2. Download each media file
for notice in manifest:
    response = requests.get(f"{base_url}/api/media/{notice['filename']}", headers=headers)
    with open(notice['filename'], 'wb') as f:
        f.write(response.content)
```

---

## 8. Project Structure

```
kimfrankjerry-Noticeboard/
│
├── app.py                  # Application factory (create_app), extension init, blueprint registration
├── config.py               # Centralised configuration (SECRET_KEY, DB URI, UPLOAD_FOLDER, API_TOKEN)
├── models.py               # SQLAlchemy ORM models (User, Notice, Playlist, AuditLog)
│
├── routes/
│   ├── admin.py            # Admin blueprint — all CMS web UI routes (/admin/*)
│   ├── api.py              # API blueprint — REST endpoints for the Raspberry Pi (/api/*)
│   ├── auth.py             # Auth blueprint — login, logout, change-password (/login, /logout)
│   └── utils.py            # Shared helper utilities
│
├── templates/
│   ├── base.html           # Jinja2 base template (nav, flash messages, layout)
│   ├── login.html          # Admin login page
│   ├── dashboard.html      # Summary dashboard with notice counts
│   ├── notices.html        # Paginated notice management table
│   ├── upload.html         # Notice upload form (file + metadata)
│   ├── edit.html           # Notice metadata editing form
│   ├── users.html          # User management page (superadmin only)
│   ├── status.html         # System health & audit log page
│   └── change_password.html# Forced / voluntary password change form
│
├── static/
│   ├── css/
│   │   └── style.css       # Application stylesheet
│   └── js/
│       └── main.js         # Client-side JavaScript
│
├── media/                  # (Runtime — gitignored) Uploaded media files stored here
├── kiosk.db                # (Runtime — gitignored) SQLite database file
├── sync_log.txt            # (Runtime — optional) Written by Pi sync agent after each sync
│
├── .gitignore              # Excludes venv/, __pycache__/, kiosk.db, media/, .env
└── README.md               # This file
```

---

## 9. Database Schema

The application uses **SQLite** with four tables managed by Flask-SQLAlchemy.

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment primary key |
| `username` | VARCHAR(80) | Unique, not null |
| `password_hash` | VARCHAR(200) | bcrypt hash — never plain text |
| `role` | VARCHAR(20) | `superadmin` or `editor` |
| `created_at` | DATETIME | Set by SQL `now()` on insert |
| `force_password_change` | BOOLEAN | If `True`, user is redirected to change-password on login |

### `notices`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment primary key |
| `title` | VARCHAR(200) | Display title |
| `filename` | VARCHAR(200) | Saved filename in `media/` folder |
| `content_type` | VARCHAR(20) | MIME type (e.g. `image/jpeg`) |
| `duration` | INTEGER | Display time in seconds (default: 10) |
| `priority` | INTEGER | Higher = shown first (default: 1) |
| `valid_from` | DATETIME | Notice display window start |
| `valid_until` | DATETIME | Notice display window end |
| `uploaded_by` | INTEGER (FK) | References `users.id` |
| `created_at` | DATETIME | Upload timestamp |
| `status` | VARCHAR(20) | `published` or `draft` — only published notices appear on the Pi |

### `playlist`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment primary key |
| `notice_id` | INTEGER (FK) | References `notices.id` |
| `display_order` | INTEGER | Position in the playlist |
| `active` | BOOLEAN | Whether this playlist entry is active |

### `audit_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment primary key |
| `user_id` | INTEGER (FK) | References `users.id` |
| `action` | VARCHAR(200) | Description of the action taken |
| `target` | VARCHAR(200) | The subject of the action (nullable) |
| `timestamp` | DATETIME | When the action occurred |

---

## 10. Admin Web Interface Routes (Reference)

| Method | Route | Access | Description |
|---|---|---|---|
| `GET/POST` | `/login` | Public | Admin login page |
| `GET` | `/logout` | Logged In | Ends the session |
| `GET/POST` | `/change-password` | Logged In | Change own password |
| `GET` | `/admin/dashboard` | Logged In | Summary overview |
| `GET` | `/admin/notices` | Logged In | Paginated notice list |
| `GET/POST` | `/admin/upload` | Logged In | Upload new notice |
| `GET/POST` | `/admin/edit/<id>` | Logged In | Edit notice metadata |
| `POST` | `/admin/delete/<id>` | Logged In | Delete a notice |
| `POST` | `/admin/notices/bulk-delete` | Superadmin | Delete multiple notices |
| `GET` | `/admin/users` | Superadmin | User management |
| `POST` | `/admin/users/create` | Superadmin | Create a new user |
| `POST` | `/admin/users/delete/<id>` | Superadmin | Delete a user |
| `POST` | `/admin/users/role/<id>` | Superadmin | Change a user's role |
| `POST` | `/admin/users/<id>/reset-password` | Superadmin | Generate temporary password |
| `GET` | `/admin/status` | Logged In | System health dashboard |

---

*Smart Kiosk CMS — PRJ017 | Built with Flask, Flask-SQLAlchemy, Flask-Login, Flask-Bcrypt & Pillow*

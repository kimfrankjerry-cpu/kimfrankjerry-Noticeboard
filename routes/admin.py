"""
routes/admin.py
===============
Admin blueprint — all routes that the CMS browser interface uses.

Routes in this file:
  GET  /admin/dashboard          — Summary cards + recent notices
  GET  /admin/notices            — Full paginated notice table
  GET/POST /admin/upload         — Upload a new notice (file + metadata)
  GET/POST /admin/edit/<id>      — Edit an existing notice's metadata
  POST /admin/delete/<id>        — Delete a notice and its media file
  GET  /admin/users              — List all users (superadmin only)
  POST /admin/users/create       — Create a new user (superadmin only)
  POST /admin/users/delete/<id>  — Delete a user (superadmin only)
  POST /admin/users/role/<id>    — Change a user's role (superadmin only)
  GET  /admin/status             — System health dashboard (FR-10)

All routes require login (via @login_required from Flask-Login).
Superadmin-only routes additionally check current_user.role.
"""

import os
import time                       # Used to calculate server uptime
from datetime import datetime     # Used for notice validity windows and status badges

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, abort, send_from_directory
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename  # Sanitises uploaded filenames to prevent path attacks
from models import db, Notice, User, AuditLog
import secrets

def log_action(action, target=None):
    if current_user and current_user.is_authenticated:
        log = AuditLog(user_id=current_user.id, action=action, target=target)
        db.session.add(log)
        db.session.commit()

# Create the blueprint with a URL prefix so all routes here start with /admin
admin = Blueprint('admin', __name__, url_prefix='/admin')

# Record when the application started — used by the /status route to calculate uptime
APP_START_TIME = time.time()


# ------------------------------------------------------------------ #
# Helper functions
# ------------------------------------------------------------------ #

def allowed_file(filename):
    """
    Return True if the filename has an extension that is in ALLOWED_EXTENSIONS.
    This prevents users from uploading executable scripts disguised as images.
    """
    # Check there is a dot in the filename (rules out files like 'noextension')
    # then check the part after the last dot is in our allowed set
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def notice_status(notice):
    """
    Derive the display status of a notice based on today's date/time.

    Returns one of three strings:
        'active'    — the notice is currently being shown on the kiosk
        'scheduled' — the notice starts in the future
        'expired'   — the notice's end date has passed
    """
    now = datetime.utcnow()
    if notice.valid_until < now:
        return 'expired'    # End date is in the past
    elif notice.valid_from > now:
        return 'scheduled'  # Start date is still in the future
    else:
        return 'active'     # Now falls between start and end dates


# ------------------------------------------------------------------ #
# Dashboard
# ------------------------------------------------------------------ #

@admin.route('/dashboard')
@login_required  # Flask-Login redirects to /login if the user is not authenticated
def dashboard():
    """
    GET /admin/dashboard

    Shows summary cards with counts of total / active / scheduled / expired
    notices, plus the five most recently uploaded notices as a quick overview.

    Maps to: FR-02 (administrator overview screen).
    """
    all_notices = Notice.query.all()  # Fetch every notice for counting

    # Calculate counts by checking each notice's status
    total = len(all_notices)
    active_count    = sum(1 for n in all_notices if notice_status(n) == 'active')
    scheduled_count = sum(1 for n in all_notices if notice_status(n) == 'scheduled')
    expired_count   = sum(1 for n in all_notices if notice_status(n) == 'expired')

    # Fetch the 5 most recently uploaded notices for the "recent activity" section
    recent = Notice.query.order_by(Notice.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total=total,
        active_count=active_count,
        scheduled_count=scheduled_count,
        expired_count=expired_count,
        recent=recent,
        notice_status=notice_status,  # Pass the helper function so the template can use it
    )


# ------------------------------------------------------------------ #
# Notices list
# ------------------------------------------------------------------ #

@admin.route('/preview/<path:filename>')
@login_required
def preview(filename):
    """
    GET /admin/preview/<filename>

    Serves a media file from UPLOAD_FOLDER to the browser admin interface.
    This is a browser-facing route protected by Flask-Login (session cookie).

    It is distinct from /api/media/<filename> which is protected by the API
    bearer token and is used by the Raspberry Pi sync agent.
    send_from_directory() prevents directory traversal attacks.
    """
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@admin.route('/notices')
@login_required
def notices():
    """
    GET /admin/notices

    Full table of all notices with edit/delete buttons and status badges.
    Maps to: FR-03 (notice management screen).
    """
    page = request.args.get('page', 1, type=int)
    notices_pagination = Notice.query.order_by(Notice.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    
    return render_template(
        'notices.html',
        notices=notices_pagination.items,
        pagination=notices_pagination,
        notice_status=notice_status,  # Pass helper so template can compute each badge
    )


# ------------------------------------------------------------------ #
# Upload notice
# ------------------------------------------------------------------ #

@admin.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """
    GET  /admin/upload — Shows the upload form.
    POST /admin/upload — Saves the uploaded file and database record.

    Maps to: FR-04 (content upload).
    """
    if request.method == 'POST':
        # ---- Collect form data ---- #
        title    = request.form.get('title', '').strip()
        duration = request.form.get('duration', type=int, default=10)
        priority = request.form.get('priority', type=int, default=1)
        status   = request.form.get('status', 'published')

        valid_from_str  = request.form.get('valid_from')
        valid_until_str = request.form.get('valid_until')

        # Convert HTML datetime-local strings ("2025-12-01T09:00") to Python datetime objects
        valid_from  = datetime.strptime(valid_from_str,  '%Y-%m-%dT%H:%M') if valid_from_str  else datetime.utcnow()
        valid_until = datetime.strptime(valid_until_str, '%Y-%m-%dT%H:%M') if valid_until_str else datetime.utcnow()

        # ---- Validate the file ---- #
        if 'file' not in request.files:
            flash('No file detected in the form.', 'danger')
            return redirect(request.url)

        file = request.files['file']  # The werkzeug FileStorage object

        if file.filename == '':
            flash('No file selected — please choose a file.', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('File type not allowed. Upload PNG, JPG, JPEG, or MP4 only.', 'danger')
            return redirect(request.url)

        # ---- Save the file to disk ---- #
        # secure_filename() strips dangerous characters like "../" from the name
        filename = secure_filename(file.filename)

        # Create the media folder if it doesn't exist yet (first upload ever)
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)  # Write the bytes to the Pi's SD card / SSD

        # --- Auto-resize massive images to fit within Kiosk max resolution --- #
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            from PIL import Image
            try:
                img = Image.open(file_path)
                # If image is larger than 1920x1080, resize it proportionally
                max_size = (1920, 1080)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(file_path)
            except Exception as e:
                pass  # If resizing fails, just continue with original file

        # ---- Save the record to the database ---- #
        new_notice = Notice(
            title        = title,
            filename     = filename,
            content_type = file.mimetype,  # e.g. "image/jpeg" or "video/mp4"
            duration     = duration,
            priority     = priority,
            valid_from   = valid_from,
            valid_until  = valid_until,
            uploaded_by  = current_user.id, # current_user is set by Flask-Login
            status       = status
        )
        db.session.add(new_notice)
        db.session.commit()  # Write to the SQLite database file
        
        log_action(f"Uploaded notice: {title}")

        flash(f'Notice "{title}" uploaded successfully!', 'success')
        return redirect(url_for('admin.notices'))

    # GET request — just render the blank form
    return render_template('upload.html')


# ------------------------------------------------------------------ #
# Edit notice
# ------------------------------------------------------------------ #

@admin.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """
    GET  /admin/edit/<id> — Shows the edit form pre-filled with current values.
    POST /admin/edit/<id> — Updates the notice metadata in the database.

    Note: Editing does NOT allow changing the media file itself — only the
    title, duration, priority, and validity window.  The file can be
    replaced by deleting and re-uploading.

    Maps to: FR-05 (content editing).
    """
    # get_or_404 returns the notice with this id, or Flask returns a 404 page
    notice = Notice.query.get_or_404(id)

    if request.method == 'POST':
        # Read the updated values from the submitted form
        notice.title    = request.form.get('title', notice.title).strip()
        notice.duration = request.form.get('duration', type=int, default=notice.duration)
        notice.priority = request.form.get('priority', type=int, default=notice.priority)
        notice.status   = request.form.get('status', notice.status)

        valid_from_str  = request.form.get('valid_from')
        valid_until_str = request.form.get('valid_until')

        # Only update dates if the form fields were filled in
        if valid_from_str:
            notice.valid_from  = datetime.strptime(valid_from_str,  '%Y-%m-%dT%H:%M')
        if valid_until_str:
            notice.valid_until = datetime.strptime(valid_until_str, '%Y-%m-%dT%H:%M')

        # SQLAlchemy tracks which fields changed and writes only those columns
        db.session.commit()

        log_action(f"Edited notice: {notice.title}")

        flash(f'Notice "{notice.title}" updated successfully.', 'success')
        return redirect(url_for('admin.notices'))

    # GET — render the form with the existing values pre-filled
    return render_template('edit.html', notice=notice)


# ------------------------------------------------------------------ #
# Delete notice
# ------------------------------------------------------------------ #

@admin.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """
    POST /admin/delete/<id>

    Deletes the notice record from the database AND removes the media file
    from disk. We use POST (not GET) so that a search crawler or browser
    prefetch can never accidentally trigger a deletion.

    Maps to: FR-06 (content deletion).
    """
    notice = Notice.query.get_or_404(id)

    # Remove the physical file from the SD card to free storage space
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], notice.filename)
    if os.path.exists(file_path):
        os.remove(file_path)  # os.remove() deletes a single file (not a directory)

    # Remove the database record
    db.session.delete(notice)
    db.session.commit()
    
    log_action(f"Deleted notice: {notice.title}")

    flash(f'Notice "{notice.title}" deleted.', 'success')
    return redirect(url_for('admin.notices'))

@admin.route('/notices/bulk-delete', methods=['POST'])
@login_required
def bulk_delete():
    if current_user.role != 'superadmin':
        abort(403)
        
    notice_ids = request.form.getlist('notice_ids')
    count = 0
    for nid in notice_ids:
        notice = Notice.query.get(int(nid))
        if notice:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], notice.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            log_action(f"Deleted notice: {notice.title}")
            db.session.delete(notice)
            count += 1
            
    db.session.commit()
    flash(f'{count} notices successfully deleted.', 'success')
    return redirect(url_for('admin.notices'))

# ------------------------------------------------------------------ #
# User management — superadmin only
# ------------------------------------------------------------------ #

@admin.route('/users')
@login_required
def users():
    """
    GET /admin/users

    Lists all user accounts.  Only superadmins may view this page.
    Maps to: FR-07 (user management).
    """
    # Enforce superadmin-only access — abort(403) sends a "Forbidden" HTTP response
    if current_user.role != 'superadmin':
        abort(403)

    all_users = User.query.order_by(User.id).all()  # All users sorted by creation order
    return render_template('users.html', users=all_users)


@admin.route('/users/create', methods=['POST'])
@login_required
def create_user():
    """
    POST /admin/users/create

    Creates a new user account.  Only superadmins may do this.
    The password is hashed before storage — never stored in plain text.

    Maps to: FR-07 (user creation).
    """
    if current_user.role != 'superadmin':
        abort(403)

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role     = request.form.get('role', 'editor')  # Default to editor — least privilege principle

    # Validate that we have both a username and a password
    if not username or not password:
        flash('Username and password are both required.', 'danger')
        return redirect(url_for('admin.users'))

    # Check the username is not already taken
    existing = User.query.filter_by(username=username).first()
    if existing:
        flash(f'Username "{username}" is already in use. Choose a different name.', 'danger')
        return redirect(url_for('admin.users'))

    # Validate role is one of the two allowed values
    if role not in ('superadmin', 'editor'):
        flash('Invalid role. Choose superadmin or editor.', 'danger')
        return redirect(url_for('admin.users'))

    # Import bcrypt here to avoid circular-import issues at module load time
    from app import bcrypt
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(username=username, password_hash=hashed_pw, role=role)
    db.session.add(new_user)
    db.session.commit()

    log_action(f"Created user: {username}")

    flash(f'User "{username}" created successfully with role "{role}".', 'success')
    return redirect(url_for('admin.users'))


@admin.route('/users/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    """
    POST /admin/users/delete/<id>

    Deletes a user account.  Only superadmins may do this.
    Prevents deleting your own account (that would lock you out).

    Maps to: FR-07 (user deletion).
    """
    if current_user.role != 'superadmin':
        abort(403)

    user = User.query.get_or_404(id)

    # Safety check — you cannot delete yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account while logged in.', 'warning')
        return redirect(url_for('admin.users'))

    db.session.delete(user)
    db.session.commit()

    log_action(f"Deleted user: {user.username}")

    flash(f'User "{user.username}" deleted.', 'success')
    return redirect(url_for('admin.users'))


@admin.route('/users/role/<int:id>', methods=['POST'])
@login_required
def change_role(id):
    """
    POST /admin/users/role/<id>

    Changes a user's role between 'superadmin' and 'editor'.
    Only superadmins may promote or demote other users.

    Maps to: FR-07 (role management).
    """
    if current_user.role != 'superadmin':
        abort(403)

    user    = User.query.get_or_404(id)
    new_role = request.form.get('role', 'editor')

    if new_role not in ('superadmin', 'editor'):
        flash('Invalid role value.', 'danger')
        return redirect(url_for('admin.users'))

    user.role = new_role
    db.session.commit()

    log_action(f"Changed role of {user.username} to {new_role}")

    flash(f'Role for "{user.username}" changed to "{new_role}".', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
def reset_password(id):
    if current_user.role != 'superadmin':
        abort(403)
    user = User.query.get_or_404(id)
    temp_pw = secrets.token_urlsafe(9)
    from app import bcrypt
    user.password_hash = bcrypt.generate_password_hash(temp_pw).decode('utf-8')
    user.force_password_change = True
    db.session.commit()
    
    log_action(f"Reset password for user: {user.username}")
    flash(f'TEMPORARY_PASSWORD:{temp_pw}', 'temp_password')
    return redirect(url_for('admin.users'))

# ------------------------------------------------------------------ #
# System status
# ------------------------------------------------------------------ #

@admin.route('/status')
@login_required
def status():
    """
    GET /admin/status

    Displays a real-time health dashboard for the kiosk system:
      - Server uptime (calculated from APP_START_TIME)
      - Number of media files in UPLOAD_FOLDER
      - Total storage used by media files (in MB)
      - Last successful sync timestamp (read from sync_log.txt if present)

    The page auto-refreshes every 30 seconds (controlled in the template).

    Maps to: FR-10 (system status monitoring).
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']

    # ---- Count files and calculate storage used ---- #
    file_count   = 0  # Number of media files
    total_bytes  = 0  # Cumulative size of all media files in bytes

    if os.path.isdir(upload_folder):
        for fname in os.listdir(upload_folder):  # Iterate over every item in the media folder
            fpath = os.path.join(upload_folder, fname)
            if os.path.isfile(fpath):            # Skip subdirectories (if any)
                file_count  += 1
                total_bytes += os.path.getsize(fpath)  # File size in bytes

    # Convert bytes to megabytes with two decimal places for readability
    storage_mb = round(total_bytes / (1024 * 1024), 2)

    # ---- Calculate server uptime ---- #
    elapsed_seconds = int(time.time() - APP_START_TIME)  # Seconds since Flask started
    # Break into hours, minutes, seconds for a human-readable format
    hours,   remainder = divmod(elapsed_seconds, 3600)
    minutes, seconds   = divmod(remainder, 60)
    uptime_str = f'{hours}h {minutes}m {seconds}s'

    # ---- Read last sync timestamp from log file ---- #
    # The Pi sync agent writes a line to sync_log.txt after each successful sync.
    # If the file doesn't exist yet (no sync has happened), we show "Never".
    sync_log_path = os.path.join(current_app.config['BASEDIR'], 'sync_log.txt')
    last_sync = 'Never'  # Default value shown before first sync

    if os.path.exists(sync_log_path):
        try:
            with open(sync_log_path, 'r') as f:
                lines = f.readlines()            # Read all lines from the log file
                if lines:
                    # The last line in the file is the most recent sync entry
                    last_sync = lines[-1].strip()
        except IOError:
            # If the file can't be read (permissions issue), keep the default
            last_sync = 'Unable to read log file'

    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all()

    return render_template(
        'status.html',
        file_count   = file_count,
        storage_mb   = storage_mb,
        uptime       = uptime_str,
        last_sync    = last_sync,
        recent_logs  = recent_logs,
    )
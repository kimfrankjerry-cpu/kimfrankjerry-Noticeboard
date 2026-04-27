import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Notice

# Create the Blueprint, prefixing all routes with '/admin'
admin = Blueprint('admin', __name__, url_prefix='/admin')

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@admin.route('/dashboard')
@login_required
def dashboard():
    # Retrieve all notices from the database, ordered by newest first
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return render_template('dashboard.html', notices=notices)

@admin.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # 1. Grab text data from the HTML form
        title = request.form.get('title')
        duration = request.form.get('duration', type=int, default=10)
        priority = request.form.get('priority', type=int, default=1)
        
        valid_from_str = request.form.get('valid_from')
        valid_until_str = request.form.get('valid_until')
        
        # Convert HTML datetime strings into Python datetime objects
        valid_from = datetime.strptime(valid_from_str, '%Y-%m-%dT%H:%M') if valid_from_str else datetime.utcnow()
        valid_until = datetime.strptime(valid_until_str, '%Y-%m-%dT%H:%M') if valid_until_str else datetime.utcnow()

        # 2. Check if a file was actually uploaded
        if 'file' not in request.files:
            flash("No file detected.")
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash("No file selected.")
            return redirect(request.url)

        # 3. Process the file and save to database
        if file:
            # Strip dangerous characters from the filename
            filename = secure_filename(file.filename)
            
            # Ensure the 'media' folder exists to prevent crashes
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Save the physical file to the Pi's storage
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Write the record to the SQLite database
            new_notice = Notice(
                title=title,
                filename=filename,
                content_type=file.mimetype,
                duration=duration,
                priority=priority,
                valid_from=valid_from,
                valid_until=valid_until,
                uploaded_by=current_user.id
            )
            db.session.add(new_notice)
            db.session.commit()
            
            flash("Notice uploaded successfully!")
            return redirect(url_for('admin.dashboard'))

    # If it's a GET request, just show the blank form
    return render_template('upload.html')

@admin.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    # Find the notice in the database or return a 404 error
    notice = Notice.query.get_or_404(id)
    
    # Delete the physical file from the SD card to conserve storage
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], notice.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        
    # Delete the record from the database
    db.session.delete(notice)
    db.session.commit()
    
    flash("Notice deleted successfully.")
    return redirect(url_for('admin.dashboard'))
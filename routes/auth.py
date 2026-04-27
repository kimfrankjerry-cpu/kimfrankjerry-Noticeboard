from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth   = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if not user:
        flash('Invalid username or password.', 'error')
        return redirect(url_for('auth.login'))
    
    # Import here to avoid circular imports
    from app import bcrypt
    if not bcrypt.check_password_hash(user.password_hash, password):
        flash('Invalid username or password.', 'error')
        return redirect(url_for('auth.login'))

    # Hand the user object to Flask-Login — it manages the session
    login_user(user)

    if user.force_password_change:
        flash('You must change your password before continuing.', 'warning')
        return redirect(url_for('auth.change_password'))

    flash('Logged in successfully.', 'success')
    return redirect(url_for('admin.dashboard'))


@auth.before_app_request
def require_password_change():
    # If the user is logged in, must change password, and is NOT already on
    # the change password page, logout page, or serving static files
    if current_user.is_authenticated and current_user.force_password_change:
        if request.endpoint and request.endpoint not in ('auth.change_password', 'auth.logout', 'static'):
            flash('You must change your password before continuing.', 'warning')
            return redirect(url_for('auth.change_password'))

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        from app import bcrypt

        if not bcrypt.check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('New password and confirm password do not match.', 'danger')
            return redirect(url_for('auth.change_password'))

        if len(new_password) < 8:
            flash('New password must be at least 8 characters long.', 'danger')
            return redirect(url_for('auth.change_password'))

        # Update the password and remove the force change flag
        hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
        current_user.password_hash = hashed_pw
        current_user.force_password_change = False
        db.session.commit()

        # Log the action
        try:
            from routes.admin import log_action
            log_action('Changed own password', None)
        except ImportError:
            pass # In case log_action isn't implemented yet

        flash('Password changed successfully!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('change_password.html')


@auth.route('/logout')
def logout():
    logout_user()  # Flask-Login clears its own session
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
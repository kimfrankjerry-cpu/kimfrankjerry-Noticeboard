from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user
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

    flash('Logged in successfully.', 'success')
    return redirect(url_for('admin.dashboard'))


@auth.route('/logout')
def logout():
    logout_user()  # Flask-Login clears its own session
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
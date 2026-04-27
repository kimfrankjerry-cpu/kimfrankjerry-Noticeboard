"""
app.py
======
Flask application factory for the Kiosk CMS (PRJ017).

The factory pattern (create_app function) means the app object is only created
when explicitly called. This makes testing and configuration swapping easy.

Start the server:
    python app.py

Default superadmin credentials (first run only):
    username: admin
    password: admin1234
"""

from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from sqlalchemy import text
from config import Config
from models import db, User

# Bcrypt is created at module level so routes/auth.py can import it.
# It is NOT yet bound to an app — that happens inside create_app() via init_app().
bcrypt = Bcrypt()


def create_app():
    """
    Create and fully configure the Flask application.
    Returns the configured app object ready to serve requests.
    """
    app = Flask(__name__)

    # Load all settings from config.py (SECRET_KEY, DB URI, UPLOAD_FOLDER, etc.)
    app.config.from_object(Config)

    # ------------------------------------------------------------------ #
    # 1. Initialise extensions — bind them to this specific app instance
    # ------------------------------------------------------------------ #

    # Bind SQLAlchemy to the app so db.session, db.create_all() etc. work
    db.init_app(app)

    # Bind Bcrypt so bcrypt.generate_password_hash() uses this app's config
    bcrypt.init_app(app)

    # Set up Flask-Login, which manages the "who is logged in" session state
    login_manager = LoginManager()
    # 'auth.login' is the endpoint name for the login page — Flask-Login
    # redirects unauthenticated users to this view automatically
    login_manager.login_view = 'auth.login'
    # Customise the flash message shown when login is required
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    # Tell Flask-Login how to reload a User object from the database given
    # a user_id stored in the session cookie. This is called on every request.
    @login_manager.user_loader
    def load_user(user_id):
        # user_id comes from the session as a string — convert to int for the query
        return User.query.filter_by(id=int(user_id)).first()

    # ------------------------------------------------------------------ #
    # 2. Register Blueprints (route collections)
    # ------------------------------------------------------------------ #

    # Auth routes: /login, /logout
    from routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # Admin routes: /admin/dashboard, /admin/upload, /admin/delete, etc.
    from routes.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    # API routes: /api/manifest, /api/media/<filename>
    # This blueprint is used by the Raspberry Pi sync agent, not by the browser
    from routes.api import api as api_blueprint
    app.register_blueprint(api_blueprint)

    # ------------------------------------------------------------------ #
    # 3. Create database tables and seed the first superadmin
    # ------------------------------------------------------------------ #
    with app.app_context():
        # db.create_all() reads all Model classes and creates tables that
        # don't exist yet. It is safe to call on every startup because it
        # does NOT drop or modify existing tables.
        db.create_all()

        # Database Migration Strategy for SQLite ALTER TABLE
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE notices ADD COLUMN status VARCHAR(20) DEFAULT 'published'"))
                conn.execute(text("ALTER TABLE users ADD COLUMN force_password_change BOOLEAN DEFAULT 0"))
                conn.commit()
        except Exception:
            pass  # Columns already exist — safe to ignore

        # ---- First-run seed ---- #
        # Check if there are ANY users in the database.
        # If not, this is a brand-new deployment and we need a default admin.
        if User.query.count() == 0:
            # Hash the default password — never store passwords as plain text!
            default_password = 'admin1234'
            hashed_pw = bcrypt.generate_password_hash(default_password).decode('utf-8')

            # Create the default superadmin account
            default_admin = User(
                username='admin',
                password_hash=hashed_pw,
                role='superadmin'   # Full access to all routes including user management
            )
            db.session.add(default_admin)
            db.session.commit()

            # Print a VERY visible warning in the terminal so the student
            # knows to change the password immediately
            print("")
            print("=" * 60)
            print("  *** FIRST-RUN SETUP: DEFAULT ADMIN CREATED ***")
            print("  Username : admin")
            print("  Password : admin1234")
            print("  ACTION REQUIRED: Change this password immediately")
            print("  after your first login via the Users page.")
            print("=" * 60)
            print("")

    # ------------------------------------------------------------------ #
    # 4. Root URL redirect
    # ------------------------------------------------------------------ #
    @app.route('/')
    def index():
        # Visiting http://server/ sends users straight to the dashboard.
        # Flask-Login will redirect unauthenticated users to /login.
        return redirect(url_for('admin.dashboard'))

    return app


# ------------------------------------------------------------------ #
# Entry point — only runs when you execute "python app.py" directly.
# In production with gunicorn or nginx, this block is NOT executed.
# ------------------------------------------------------------------ #
if __name__ == '__main__':
    app = create_app()
    # host='0.0.0.0' makes the server accessible from any network interface,
    # not just localhost — needed so the Pi can reach the server on the LAN.
    # debug=True shows detailed error pages — set to False in production!
    app.run(host='0.0.0.0', port=5000, debug=True)
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from config import Config
from models import db, User

bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 1. Bind the Database
    db.init_app(app)
    
    # 1b. Initialize Bcrypt
    bcrypt.init_app(app)
    
    # 2. Initialize the Login Manager (This prevents your AttributeError!)
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    # Tell Flask-Login how to load the user from the database
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.filter_by(id=int(user_id)).first()

    # 3. Register Blueprints (Routes)
    from routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from routes.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    # 4. Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    # 5. Base Route: Redirect logged-in users straight to the dashboard
    @app.route('/')
    def index():
        return redirect(url_for('admin.dashboard'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
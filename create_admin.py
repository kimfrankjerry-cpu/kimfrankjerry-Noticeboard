from app import create_app, bcrypt
from models import db, User

app = create_app()
with app.app_context():
    hashed = bcrypt.generate_password_hash('your_password').decode('utf-8')
    admin  = User(username='admin', password_hash=hashed, role='superadmin')
    db.session.add(admin)
    db.session.commit()
    print("Superadmin created.")
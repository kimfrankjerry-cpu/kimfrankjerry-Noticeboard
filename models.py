from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default='editor')
    # created_at records when the account was first made — displayed on the users management page
    # server_default uses a raw SQL expression so existing rows in the DB get NULL rather than an error
    created_at    = db.Column(db.DateTime, server_default=db.func.now())
    # Relationship: A user can upload many notices
    notices = db.relationship('Notice', backref='uploader', lazy=True)
    # Flag to force a password change on next login after an admin reset
    force_password_change = db.Column(db.Boolean, default=False)

class Notice(db.Model):
    __tablename__ = 'notices'
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    filename      = db.Column(db.String(200), nullable=False)
    content_type  = db.Column(db.String(20), nullable=False)
    duration      = db.Column(db.Integer, default=10)
    priority      = db.Column(db.Integer, default=1)
    valid_from    = db.Column(db.DateTime, nullable=False)
    valid_until   = db.Column(db.DateTime, nullable=False)
    uploaded_by   = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    # Draft or published status. Draft notices don't appear on the Pi.
    status        = db.Column(db.String(20), default='published')

class Playlist(db.Model):
    __tablename__ = 'playlist'
    id            = db.Column(db.Integer, primary_key=True)
    notice_id     = db.Column(db.Integer, db.ForeignKey('notices.id'), nullable=False)
    display_order = db.Column(db.Integer, nullable=False)
    active        = db.Column(db.Boolean, default=True)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'))
    action        = db.Column(db.String(200), nullable=False)
    target        = db.Column(db.String(200))
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to user
    user = db.relationship('User', backref='audit_logs', lazy=True)

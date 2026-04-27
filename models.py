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
    # Relationship: A user can upload many notices
    notices = db.relationship('Notice', backref='uploader', lazy=True)

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

class Playlist(db.Model):
    __tablename__ = 'playlist'
    id            = db.Column(db.Integer, primary_key=True)
    notice_id     = db.Column(db.Integer, db.ForeignKey('notices.id'), nullable=False)
    display_order = db.Column(db.Integer, nullable=False)
    active        = db.Column(db.Boolean, default=True)


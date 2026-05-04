"""
config.py
=========
Central configuration for the Kiosk CMS.

All sensitive values (SECRET_KEY, API_TOKEN) read from environment variables
with safe fallback defaults.  In production on the Raspberry Pi, set these
as real environment variables rather than relying on the defaults.
"""
import os

class Config:
    # ------------------------------------------------------------------ #
    # Flask session security key — MUST be changed in production!
    # Used to sign the browser session cookie that keeps users logged in.
    # ------------------------------------------------------------------ #
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production')

    # Absolute path to the directory containing this file (config.py)
    BASEDIR = os.path.abspath(os.path.dirname(__file__))

    # SQLite database stored in the same directory as the application
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASEDIR, 'kiosk.db')

    # Disable Flask-SQLAlchemy event tracking — saves memory; we don't need it
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Folder where uploaded media files (images, videos) are stored on disk
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'media')

    # Only these file extensions are accepted on upload — prevents uploading
    # executable files or other dangerous types
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'}

    # ------------------------------------------------------------------ #
    # API Bearer token — the Raspberry Pi sync agent must include this in
    # the Authorization header:   Authorization: Bearer <API_TOKEN>
    # Change this to a long random string in production.
    # ------------------------------------------------------------------ #
    API_TOKEN = os.environ.get('API_TOKEN', '3dbebc76-46e7-4bdb-a619-e0179124986d')
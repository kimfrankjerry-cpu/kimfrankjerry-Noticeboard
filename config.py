import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production')
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
  
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASEDIR, 'kiosk.db')
  
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload folder for media files
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'media')

    # Restrict allowed file extensions for security
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'}
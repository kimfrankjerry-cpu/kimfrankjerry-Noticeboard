"""
routes/api.py
=============
REST API Blueprint — consumed by the Raspberry Pi sync agent.

Two endpoints:
  GET /api/manifest     — Returns a JSON list of currently active notices.
                          The Pi sync agent calls this to know what to download.
  GET /media/<filename> — Serves the actual media file from disk so the Pi
                          can download the content after reading the manifest.

Authentication: Both endpoints require a bearer token in the HTTP
  Authorization header, e.g.:   Authorization: Bearer my-secret-token
  The token value is set in config.py as API_TOKEN.
  This prevents unauthorised devices from querying the API.

Maps to: FR-09 (REST API), FR-10 (sync pipeline) in the project requirements.
"""

import os
import hashlib  # hashlib provides MD5 checksum computation — needed by the Pi to verify downloaded files
from datetime import datetime  # Used to compare notice validity dates against the current time

from flask import Blueprint, jsonify, request, abort, send_from_directory, current_app
from models import Notice  # Import the Notice model so we can query the database

# Create the Blueprint. url_prefix='/api' means all routes here start with /api
api = Blueprint('api', __name__, url_prefix='/api')


def _check_token():
    """
    Verify the API bearer token sent by the Raspberry Pi sync agent.

    The Pi must send:   Authorization: Bearer <API_TOKEN>
    If the token is missing or wrong, we abort with 401 Unauthorized.
    This function is called at the top of every protected endpoint.
    """
    # Read the token the client sent in the Authorization header
    auth_header = request.headers.get('Authorization', '')

    # The header should look like "Bearer abc123" — split on the space
    parts = auth_header.split()  # e.g. ['Bearer', 'abc123']

    # Check we have exactly two parts and the first word is 'Bearer'
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        # Return 401 so the Pi sync agent knows it failed authentication
        abort(401, description="Missing or malformed Authorization header. Expected: Bearer <token>")

    token_provided = parts[1]  # The actual token value the client sent

    # Compare against the expected token stored in app configuration
    token_expected = current_app.config.get('API_TOKEN', 'change-this-api-token')

    if token_provided != token_expected:
        # Return 401 — wrong token
        abort(401, description="Invalid API token.")


def _compute_md5(filepath):
    """
    Compute the MD5 checksum of a file on disk.

    The Raspberry Pi sync agent uses the checksum to verify that a downloaded
    file is not corrupted.  If the checksum matches, the file is good.

    We read the file in 64 KB chunks so we never load a large video entirely
    into RAM — important on a resource-constrained Raspberry Pi.
    """
    hasher = hashlib.md5()  # Create a new MD5 hash object
    try:
        with open(filepath, 'rb') as f:  # Open the file in binary mode
            # Read 65536 bytes at a time to keep memory usage low
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)  # Feed each chunk into the hash function
        return hasher.hexdigest()  # Return the final checksum as a hex string, e.g. "d41d8cd98f00b204e9800998ecf8427e"
    except FileNotFoundError:
        # The database record exists but the file was deleted from disk —
        # return a sentinel value so the Pi knows the file is unavailable
        return "file-not-found"


@api.route('/manifest', methods=['GET'])
def manifest():
    """
    GET /api/manifest

    Returns a JSON array of all notices that are currently active.
    A notice is active when:
        valid_from  <= NOW  <=  valid_until

    The results are ordered by priority descending so the most important
    notice appears first in the playlist.

    Example response:
    [
      {
        "id": 1,
        "title": "Exam Timetable",
        "filename": "exam_tt.jpg",
        "content_type": "image/jpeg",
        "duration": 15,
        "priority": 5,
        "checksum": "d41d8cd98f00b204e9800998ecf8427e"
      }
    ]

    Maps to: FR-09 — The server must expose a manifest endpoint for the Pi.
    """
    _check_token()  # Reject the request if the bearer token is wrong

    now = datetime.utcnow()  # Get the current UTC time to compare against validity windows

    # Query only notices whose validity window contains right now.
    # Notice.valid_from <= now AND Notice.valid_until >= now
    # Order by priority DESC so priority-5 appears before priority-1 in the list.
    active_notices = (
        Notice.query
        .filter(Notice.status == 'published')
        .filter(Notice.valid_from <= now)    # notice must have already started
        .filter(Notice.valid_until >= now)   # notice must not have expired yet
        .order_by(Notice.priority.desc())    # highest priority first
        .all()
    )

    # Build the JSON response list
    result = []
    for notice in active_notices:
        # Construct the full path to the media file so we can hash it
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], notice.filename)

        result.append({
            'id':           notice.id,
            'title':        notice.title,
            'filename':     notice.filename,
            'content_type': notice.content_type,   # e.g. "image/jpeg" or "video/mp4"
            'duration':     notice.duration,        # How long to display this notice (seconds)
            'priority':     notice.priority,        # Higher number = shown more prominently
            'checksum':     _compute_md5(filepath), # MD5 hex digest of the file on disk
        })

    # jsonify() converts the Python list to a proper JSON HTTP response
    # with Content-Type: application/json — consumable by requests.get()
    return jsonify(result)


@api.route('/media/<path:filename>', methods=['GET'])
def serve_media(filename):
    """
    GET /media/<filename>

    Serves the actual media file (image or video) from the UPLOAD_FOLDER
    so the Raspberry Pi sync agent can download it after reading the manifest.

    Without this endpoint, the Pi would know WHAT files to download (from
    /api/manifest) but would have no way to actually GET them — breaking
    the entire sync pipeline.

    send_from_directory() is Flask's safe file-serving function.  It prevents
    directory-traversal attacks (e.g. ../../etc/passwd) by restricting paths
    to the specified folder.

    Maps to: FR-09 (media delivery) in the project requirements.
    """
    _check_token()  # Media files are also protected — only authorised Pi agents can download them

    upload_folder = current_app.config['UPLOAD_FOLDER']  # e.g. /home/pi/kiosk/media

    # send_from_directory streams the file to the client.
    # as_attachment=False means the browser/client receives it inline (good for streaming).
    return send_from_directory(upload_folder, filename)

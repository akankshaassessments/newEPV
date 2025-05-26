import os
import uuid
import re
import pymysql
import sys
import io
import json
from datetime import datetime, timedelta
from flask import Flask, redirect, url_for, render_template, session, jsonify, request, send_file, flash, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.storage import MemoryStorage
from flask_dance.consumer import oauth_authorized, oauth_error
from dotenv import load_dotenv
from sqlalchemy import func
from models import db, CostCenter, EmployeeDetails, SettingsFinance, ExpenseHead, EPV, EPVItem, EPVApproval, User, OAuth, init_db, CityAssignment, FinanceEntry, SupplementaryDocument
from pdf_converter import process_files
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
# Import SMTP email utilities instead of Gmail API email utilities
from smtp_email_utils import send_approval_email, send_email, send_rejection_notification_email
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import secure_filename
from PyPDF2 import PdfMerger

# Set up proper encoding for stdout and stderr to handle Unicode characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')

# Helper functions for supplementary documents feature

def send_document_request_email(epv, requested_docs):
    """Send email to the user requesting additional documents"""
    # Get the user's email
    user_email = epv.email_id

    # Create the email subject and body
    subject = f"Additional documents requested for EPV {epv.epv_id}"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Additional Documents Requested</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f8f9fa; padding: 15px; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #777; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Additional Documents Requested</h2>
            </div>
            <div class="content">
                <p>Dear {epv.employee_name},</p>

                <p>Additional documents have been requested for your expense voucher <strong>{epv.epv_id}</strong>.</p>

                <p><strong>Requested documents:</strong> {requested_docs}</p>

                <p>Please log in to the EPV system and upload the requested documents as soon as possible.
                You can upload the documents directly from the EPV record page.</p>

                <p>Thank you,<br>Finance Team</p>
            </div>

            <div class="footer">
                <p>This is an automated email from the Expense Management System. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Send the email using SMTP
    from smtp_email_utils import send_email
    send_email(user_email, subject, html_body)

def get_parent_folder_id(file_id):
    """Get the parent folder ID of a Google Drive file"""
    try:
        # Get credentials from session
        if 'google_oauth_token' in session:
            token_info = session['google_oauth_token']
            credentials = Credentials(
                token=token_info.get('access_token'),
                refresh_token=token_info.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
            )

            # Build the Drive API client
            from googleapiclient.discovery import build
            drive_service = build('drive', 'v3', credentials=credentials)

            # Get the file metadata
            file = drive_service.files().get(fileId=file_id, fields='parents').execute()

            # Return the first parent folder ID
            if 'parents' in file and file['parents']:
                return file['parents'][0]
    except Exception as e:
        print(f"Error getting parent folder ID: {str(e)}")

    return None

def upload_to_drive(file_path, filename, parent_folder_id):
    """Upload a file to Google Drive"""
    try:
        # Get credentials from session
        if 'google_oauth_token' in session:
            token_info = session['google_oauth_token']
            credentials = Credentials(
                token=token_info.get('access_token'),
                refresh_token=token_info.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
            )

            # Build the Drive API client
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            drive_service = build('drive', 'v3', credentials=credentials)

            # File metadata
            file_metadata = {
                'name': filename,
                'parents': [parent_folder_id]
            }

            # Upload the file
            media = MediaFileUpload(file_path, resumable=True)
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            # Return the file ID
            return file.get('id')
    except Exception as e:
        print(f"Error uploading to Google Drive: {str(e)}")

    return None

def merge_supplementary_document(epv, supplementary_doc):
    """Merge a supplementary document with the original PDF"""
    try:
        # Get the original PDF path
        original_pdf_path = None
        if epv.file_url and epv.file_url.startswith('/'):
            # Local file path
            original_pdf_path = epv.file_url[1:]  # Remove leading slash
        else:
            # Download from Google Drive if needed
            if epv.drive_file_id:
                # Download the file from Google Drive
                original_pdf_path = download_from_drive(epv.drive_file_id)

        if not original_pdf_path or not os.path.exists(original_pdf_path):
            raise Exception(f"Original PDF not found: {original_pdf_path}")

        # Get the supplementary document path
        supplementary_pdf_path = supplementary_doc.file_path
        if not os.path.exists(supplementary_pdf_path):
            raise Exception(f"Supplementary PDF not found: {supplementary_pdf_path}")

        # Create a new merged PDF
        merged_pdf_path = f"uploads/merged_{epv.epv_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

        # Merge the PDFs
        merger = PdfMerger()
        merger.append(original_pdf_path)
        merger.append(supplementary_pdf_path)
        merger.write(merged_pdf_path)
        merger.close()

        # Update the EPV record with the new PDF
        epv.file_url = f"/{merged_pdf_path}"

        # Upload to Google Drive if needed
        if epv.drive_file_id:
            # Upload the merged PDF to Google Drive
            parent_folder_id = get_parent_folder_id(epv.drive_file_id)
            if parent_folder_id:
                new_drive_file_id = upload_to_drive(merged_pdf_path, os.path.basename(merged_pdf_path), parent_folder_id)
                if new_drive_file_id:
                    # Update the EPV record with the new Drive file ID
                    epv.drive_file_id = new_drive_file_id

        # Save changes
        db.session.commit()

        return True
    except Exception as e:
        print(f"Error merging documents: {str(e)}")
        return False

def download_from_drive(file_id):
    """Download a file from Google Drive"""
    try:
        # Get credentials from session
        if 'google_oauth_token' in session:
            token_info = session['google_oauth_token']
            credentials = Credentials(
                token=token_info.get('access_token'),
                refresh_token=token_info.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
            )

            # Build the Drive API client
            from googleapiclient.discovery import build
            from io import BytesIO
            drive_service = build('drive', 'v3', credentials=credentials)

            # Get the file metadata
            file = drive_service.files().get(fileId=file_id, fields='name').execute()
            filename = file.get('name', f"drive_file_{file_id}.pdf")

            # Download the file
            request = drive_service.files().get_media(fileId=file_id)
            file_content = BytesIO(request.execute())

            # Save the file locally
            local_path = f"uploads/{filename}"
            with open(local_path, 'wb') as f:
                f.write(file_content.getvalue())

            return local_path
    except Exception as e:
        print(f"Error downloading from Google Drive: {str(e)}")

    return None

def notify_finance_team(epv, supplementary_doc):
    """Notify the finance team that a supplementary document has been uploaded"""
    try:
        # Get the finance team emails
        finance_emails = []

        # Get Finance and Finance Approver users
        finance_users = EmployeeDetails.query.filter(
            EmployeeDetails.role.in_(['Finance', 'Finance Approver']),
            EmployeeDetails.is_active == True
        ).all()

        # For Finance users, check if they're assigned to the EPV's city or cost center's city
        # First check if the EPV has a city field set
        if epv.city:
            for user in finance_users:
                if user.role == 'Finance Approver':
                    # Finance Approvers get all notifications
                    finance_emails.append(user.email)
                elif user.role == 'Finance':
                    # Check if this Finance user is assigned to the EPV's city
                    city_assignment = CityAssignment.query.filter_by(
                        employee_id=user.id,
                        city=epv.city,
                        is_active=True
                    ).first()
                    if city_assignment:
                        finance_emails.append(user.email)
        # If EPV doesn't have a city, fall back to cost center's city
        elif epv.cost_center_id:
            cost_center = CostCenter.query.get(epv.cost_center_id)
            if cost_center and cost_center.city:
                for user in finance_users:
                    if user.role == 'Finance Approver':
                        # Finance Approvers get all notifications
                        finance_emails.append(user.email)
                    elif user.role == 'Finance':
                        # Check if this Finance user is assigned to the cost center's city
                        city_assignment = CityAssignment.query.filter_by(
                            employee_id=user.id,
                            city=cost_center.city,
                            is_active=True
                        ).first()
                        if city_assignment:
                            finance_emails.append(user.email)
        else:
            # If no city and no cost center, notify all Finance Approvers
            for user in finance_users:
                if user.role == 'Finance Approver':
                    finance_emails.append(user.email)

        # Create the email subject and HTML body
        subject = f"Supplementary document uploaded for EPV {epv.epv_id}"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Supplementary Document Uploaded</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 15px; text-align: center; }}
                .content {{ padding: 20px; }}
                .document-details {{ background-color: #f9f9f9; padding: 15px; margin: 15px 0; border-left: 4px solid #007bff; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #777; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Supplementary Document Uploaded</h2>
                </div>
                <div class="content">
                    <p>A supplementary document has been uploaded for EPV <strong>{epv.epv_id}</strong>.</p>

                    <div class="document-details">
                        <p><strong>Employee:</strong> {epv.employee_name} ({epv.email_id})</p>
                        <p><strong>Document:</strong> {supplementary_doc.filename}</p>
                        <p><strong>Description:</strong> {supplementary_doc.description or 'No description provided'}</p>
                    </div>

                    <p>Please review the updated EPV record.</p>

                    <p>Thank you,<br>Finance Team</p>
                </div>

                <div class="footer">
                    <p>This is an automated email from the Expense Management System. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Send the email to each finance team member using SMTP
        from smtp_email_utils import send_email
        for email in finance_emails:
            send_email(email, subject, html_body)

        return True
    except Exception as e:
        print(f"Error notifying finance team: {str(e)}")
        return False

# Function to generate a distinctive cost center code
def generate_cost_center_code(cost_center_name):
    """
    Generate a cost center code for EPV IDs.

    Use the full cost center name as requested by the user.

    Args:
        cost_center_name (str): The name of the cost center

    Returns:
        str: The full cost center name
    """
    if not cost_center_name:
        return "GEN"  # Generic code if no cost center provided

    # Return the full cost center name
    # Remove any spaces or special characters that might cause issues in filenames
    # but keep underscores intact
    clean_name = ""
    for c in cost_center_name:
        if c.isalnum() or c == '_':
            clean_name += c

    return clean_name

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

# Database configuration
# Get database credentials from environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT', '3306')
db_name = os.environ.get('DB_NAME')

# URL encode the password to handle special characters like @
import urllib.parse
encoded_password = urllib.parse.quote_plus(db_password) if db_password else ''

# Construct the database URI
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Store Google credentials in app config
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
# Create the upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Custom template filters
@app.template_filter('get_cost_center_name')
def get_cost_center_name(cost_center):
    """Extract the name from a cost center object or return the value as is"""
    if cost_center is None:
        return 'N/A'
    if isinstance(cost_center, str):
        return cost_center
    if hasattr(cost_center, 'costcenter'):
        return cost_center.costcenter
    # If it's an object with __str__ method that returns '<CostCenter X>'
    cost_center_str = str(cost_center)
    if cost_center_str.startswith('<CostCenter'):
        return cost_center_str.split(' ')[1].rstrip('>')
    return cost_center_str

# Initialize the database with the app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Configure Flask-Dance with Google OAuth
blueprint = make_google_blueprint(
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    scope=[
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/drive.file'
        # Removed Gmail scope since we're now using SMTP
        # 'https://www.googleapis.com/auth/gmail.send'
    ],
    storage=MemoryStorage(),
    redirect_to='after_login',
    authorized_url='/google/authorized',
    # Request refresh token
    reprompt_consent=True,
    # Include offline access
    offline=True
)

app.register_blueprint(blueprint, url_prefix='/login')

# Helper function to ensure token is valid
def ensure_valid_token():
    """Check if the token is valid and refresh if needed"""
    # Import the google object from Flask-Dance
    from flask_dance.contrib.google import google

    if not google.authorized:
        print("DEBUG: Not authorized with Google in ensure_valid_token")
        return False

    try:
        # Try to make a simple API call to check token validity
        print("DEBUG: Making API call to check token validity")
        resp = google.get('/oauth2/v2/userinfo')
        if resp.ok:
            print("DEBUG: Token is valid")
            return True

        # If we get here, the token might be expired but Flask-Dance should have refreshed it
        # If it didn't refresh, we have a problem
        print("WARNING: Token validation failed even after potential refresh")
        print(f"DEBUG: Response status code: {resp.status_code}")
        print(f"DEBUG: Response text: {resp.text}")
        return False
    except Exception as e:
        print(f"ERROR: Token validation failed: {str(e)}")
        import traceback
        print(f"DEBUG: Token validation traceback: {traceback.format_exc()}")
        return False

# Helper function to get Google credentials from Flask-Dance token
def get_google_credentials(scopes=None):
    """Get Google credentials from Flask-Dance token"""
    if not google.authorized:
        print("Not authorized with Google")
        return None

    if scopes is None:
        scopes = ['https://www.googleapis.com/auth/drive.file']  # Removed Gmail scope

    token_info = google.token
    print(f"Token info keys: {token_info.keys()}")

    # Check if we have a refresh token
    refresh_token = token_info.get('refresh_token')
    if not refresh_token:
        print("WARNING: No refresh token in the token info. Token will not be refreshable.")
        print("This may cause issues with long-running operations or when tokens expire.")
        print("Try logging out and logging back in with prompt='consent' to get a refresh token.")
    else:
        print("Refresh token is available")

    # Create credentials object
    credentials = Credentials(
        token=token_info['access_token'],
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        scopes=scopes
    )

    return credentials

# Set up OAuth token event handlers
@oauth_authorized.connect_via(blueprint)
def google_logged_in(blueprint, token):
    if not token:
        flash("Failed to log in with Google.", category="error")
        return False

    # Get user info from Google
    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", category="error")
        return False

    user_info = resp.json()
    email = user_info["email"]

    # Find or create the user
    try:
        # Try to find the user first
        user = User.query.filter_by(email=email).first()
        if not user:
            # Check if user exists in EmployeeDetails
            employee = EmployeeDetails.query.filter_by(email=email).first()
            if employee:
                # Create user from employee details
                user = User(
                    email=email,
                    name=employee.name,
                    role=employee.role,
                    employee_id=employee.employee_id
                )
            else:
                # Create basic user
                user = User(
                    email=email,
                    name=user_info.get('name', ''),
                    role='user'
                )

            db.session.add(user)
            db.session.commit()

        # Log in the user
        login_user(user)

        # Store user info and token in session for backward compatibility
        session['user_info'] = user_info
        session['email'] = email

        # Store token in session for backward compatibility with existing code
        session['google_token'] = token

        # Store client credentials in session for drive_utils.py
        session['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
        session['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

        # Store employee details in session if available
        employee = EmployeeDetails.query.filter_by(email=email).first()
        if employee:
            session['employee_role'] = employee.role
            session['employee_manager'] = employee.manager
            session['employee_id'] = employee.employee_id
        else:
            session['employee_role'] = None
            session['employee_manager'] = None
            session['employee_id'] = None

        # Check if user is a cost center approver
        cost_center_approver = CostCenter.query.filter_by(approver_email=email, is_active=True).first()
        session['is_cost_center_approver'] = cost_center_approver is not None
        print(f"DEBUG: User {email} is_cost_center_approver: {session['is_cost_center_approver']}")
        if cost_center_approver:
            print(f"DEBUG: User is approver for cost center: {cost_center_approver.costcenter}")

        print(f"DEBUG: Successfully logged in user: {email}")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        flash("An error occurred during login.", category="error")
        return False

    # Don't save the token again, Flask-Dance will do it for us
    return False

@oauth_error.connect_via(blueprint)
def google_error(blueprint, error, error_description=None, error_uri=None):
    msg = f"OAuth error from {blueprint.name}! {error}"
    if error_description:
        msg += f" Description: {error_description}"

    flash(msg, category="error")
    print(f"ERROR: {msg}")

# Routes
@app.route('/')
def index():
    # Check if user is logged in
    user_info = session.get('user_info')
    if user_info:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login')
def login():
    # Store the original URL the user was trying to access
    next_url = request.args.get('next') or request.referrer or '/dashboard'
    session['next_url'] = next_url
    print(f"DEBUG: Storing next_url in session: {next_url}")

    # Redirect to Google OAuth login
    return redirect(url_for('google.login'))

@app.route('/refresh-token')
def refresh_token():
    """Explicitly refresh the Google OAuth token"""
    # Check if user is logged in
    if not current_user.is_authenticated:
        flash("You must be logged in to refresh your token.")
        return redirect(url_for('login'))

    # Check if user has a Google token
    if not google.authorized:
        flash("No Google token found to refresh.")
        return redirect(url_for('login'))

    try:
        # Force a token refresh by making a request and handling any errors
        resp = google.get('/oauth2/v2/userinfo')
        if resp.ok:
            flash("Token refreshed successfully.")

            # Store token in session for backward compatibility with existing code
            session['google_token'] = google.token

            # Store client credentials in session for drive_utils.py
            session['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
            session['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
        else:
            # If the request failed, try to get a new token
            return redirect(url_for('google.login'))
    except Exception as e:
        flash(f"Error refreshing token: {str(e)}")
        return redirect(url_for('google.login'))

    # Redirect back to the page they came from or dashboard
    next_url = request.args.get('next') or request.referrer or url_for('dashboard')
    return redirect(next_url)

@app.route('/debug-token')
def debug_token():
    """Debug route to check token status"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'})

    result = {
        'google_authorized': google.authorized,
        'session_has_token': 'google_token' in session,
        'session_has_client_id': 'GOOGLE_CLIENT_ID' in session,
        'session_has_client_secret': 'GOOGLE_CLIENT_SECRET' in session,
        'app_config_has_client_id': 'GOOGLE_CLIENT_ID' in app.config and app.config['GOOGLE_CLIENT_ID'] is not None,
        'app_config_has_client_secret': 'GOOGLE_CLIENT_SECRET' in app.config and app.config['GOOGLE_CLIENT_SECRET'] is not None,
    }

    if google.authorized:
        token_info = google.token
        result['token_keys'] = list(token_info.keys())
        result['has_access_token'] = 'access_token' in token_info
        result['has_refresh_token'] = 'refresh_token' in token_info

    if 'google_token' in session:
        token_info = session['google_token']
        if isinstance(token_info, dict):
            result['session_token_keys'] = list(token_info.keys())
            result['session_has_access_token'] = 'access_token' in token_info
            result['session_has_refresh_token'] = 'refresh_token' in token_info
        else:
            result['session_token_type'] = type(token_info).__name__

    return jsonify(result)

@app.route('/debug-session')
def debug_session():
    """Debug route to check session data"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'})

    # Get user email from session
    email = session.get('email')

    # Check if user is a cost center approver
    with app.app_context():
        cost_center = CostCenter.query.filter_by(approver_email=email, is_active=True).first()

    # Prepare result
    result = {
        'email': email,
        'is_cost_center_approver_in_session': session.get('is_cost_center_approver'),
        'is_cost_center_approver_in_db': cost_center is not None,
        'cost_center_name': cost_center.costcenter if cost_center else None,
        'session_keys': list(session.keys())
    }

    # Update the session value
    session['is_cost_center_approver'] = cost_center is not None
    result['is_cost_center_approver_updated'] = session.get('is_cost_center_approver')

    return jsonify(result)

@app.route('/logout-user')
def logout_user_route():
    # Revoke token if available
    if google.authorized:
        try:
            token = google.token["access_token"]
            resp = google.post(
                "https://accounts.google.com/o/oauth2/revoke",
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            print(f"DEBUG: Token revocation response: {resp.text}")
        except Exception as e:
            print(f"DEBUG: Error revoking token: {str(e)}")

    # Clear Flask-Login session
    logout_user()

    # Clear Flask session
    session.clear()

    flash("You have been logged out.")
    return redirect(url_for('index'))

@app.route('/after-login')
def after_login():
    # Check if user is authenticated with Google
    if not google.authorized:
        flash("Authentication failed.")
        return redirect(url_for('index'))

    # Get user info from Google
    resp = google.get('/oauth2/v2/userinfo')
    if not resp.ok:
        flash("Failed to get user info from Google.")
        return redirect(url_for('index'))

    user_info = resp.json()
    email = user_info['email']

    # Find or create user
    user = User.query.filter_by(email=email).first()
    if not user:
        # Check if user exists in EmployeeDetails
        employee = EmployeeDetails.query.filter_by(email=email).first()
        if employee:
            # Create user from employee details
            user = User(
                email=email,
                name=employee.name,
                role=employee.role,
                employee_id=employee.employee_id
            )
        else:
            # Create basic user
            user = User(
                email=email,
                name=user_info.get('name', ''),
                role='user'
            )

        db.session.add(user)
        db.session.commit()

    # Log in the user with Flask-Login
    login_user(user)

    # Store user info in session for backward compatibility
    session['user_info'] = user_info
    session['email'] = email

    # Check if user is a cost center approver
    cost_center_approver = CostCenter.query.filter_by(approver_email=email, is_active=True).first()
    session['is_cost_center_approver'] = cost_center_approver is not None
    print(f"DEBUG: User {email} is_cost_center_approver: {session['is_cost_center_approver']}")
    if cost_center_approver:
        print(f"DEBUG: User is approver for cost center: {cost_center_approver.costcenter}")

    # Get the next URL from session
    next_url = session.get('next_url', '/dashboard')

    # Redirect to the next URL
    return redirect(next_url)

@app.route('/settings')
@login_required
def settings():
    """Settings page with tabs for Cost Centers, Employees, Expense Heads, and Finance Settings"""
    # Check if user is Super Admin or Finance Approver
    employee_role = session.get('employee_role')
    if employee_role not in ['Super Admin', 'Finance Approver']:
        flash('You do not have permission to access settings.', 'error')
        return redirect(url_for('dashboard'))

    # Get data for all tabs
    cost_centers = CostCenter.query.all()
    employees = EmployeeDetails.query.all()
    expense_heads = ExpenseHead.query.all()

    # Get finance settings
    finance_settings = {}
    finance_settings_records = SettingsFinance.query.all()
    for setting in finance_settings_records:
        finance_settings[setting.setting_name] = setting.setting_value

    # Get finance settings log (for the change log table)
    finance_settings_log = SettingsFinance.query.filter(
        SettingsFinance.updated_by.isnot(None),
        SettingsFinance.previous_value.isnot(None)
    ).order_by(SettingsFinance.updated_on.desc()).limit(10).all()

    return render_template('settings.html',
                          user=session.get('user_info'),
                          cost_centers=cost_centers,
                          employees=employees,
                          expense_heads=expense_heads,
                          finance_settings=finance_settings,
                          finance_settings_log=finance_settings_log)

@app.route('/update-finance-settings', methods=['POST'])
@login_required
def update_finance_settings():
    """Update finance settings"""
    # Check if user is Super Admin or Finance Approver
    employee_role = session.get('employee_role')
    if employee_role not in ['Super Admin', 'Finance Approver']:
        flash('You do not have permission to update finance settings.', 'error')
        return redirect(url_for('dashboard'))

    # Get the user's email
    user_email = session.get('email')

    # Get values from the form
    max_days_processing = request.form.get('max_days_processing')
    max_days_past = request.form.get('max_days_past')

    # Validate max_days_processing
    try:
        max_days_processing_int = int(max_days_processing)
        if max_days_processing_int < 1 or max_days_processing_int > 200:
            flash('Maximum processing days must be between 1 and 200.', 'error')
            return redirect(url_for('settings'))
    except (ValueError, TypeError):
        flash('Maximum processing days must be a valid number.', 'error')
        return redirect(url_for('settings'))

    # Validate max_days_past
    try:
        max_days_past_int = int(max_days_past)
        if max_days_past_int < 1 or max_days_past_int > 365:
            flash('Maximum days in past must be between 1 and 365.', 'error')
            return redirect(url_for('settings'))
    except (ValueError, TypeError):
        flash('Maximum days in past must be a valid number.', 'error')
        return redirect(url_for('settings'))

    # Update max_days_processing setting
    max_days_processing_setting = SettingsFinance.query.filter_by(setting_name='max_days_processing').first()

    if max_days_processing_setting:
        # Store the previous value
        previous_value = max_days_processing_setting.setting_value

        # Update the setting if it's different
        if previous_value != max_days_processing:
            max_days_processing_setting.previous_value = previous_value
            max_days_processing_setting.setting_value = max_days_processing
            max_days_processing_setting.updated_by = user_email
            max_days_processing_setting.updated_on = datetime.now()
            db.session.commit()

            flash(f'Maximum processing days updated from {previous_value} to {max_days_processing}.', 'success')
    else:
        # Create a new setting if it doesn't exist
        max_days_processing_setting = SettingsFinance(
            setting_name='max_days_processing',
            setting_value=max_days_processing,
            description='Maximum number of days for processing expenses (SOP)',
            updated_by=user_email,
            updated_on=datetime.now()
        )
        db.session.add(max_days_processing_setting)
        db.session.commit()

        flash(f'Maximum processing days set to {max_days_processing}.', 'success')

    # Update max_days_past setting
    max_days_past_setting = SettingsFinance.query.filter_by(setting_name='max_days_past').first()

    if max_days_past_setting:
        # Store the previous value
        previous_value = max_days_past_setting.setting_value

        # Update the setting if it's different
        if previous_value != max_days_past:
            max_days_past_setting.previous_value = previous_value
            max_days_past_setting.setting_value = max_days_past
            max_days_past_setting.updated_by = user_email
            max_days_past_setting.updated_on = datetime.now()
            db.session.commit()

            flash(f'Maximum days in past for claims updated from {previous_value} to {max_days_past}.', 'success')
    else:
        # Create a new setting if it doesn't exist
        max_days_past_setting = SettingsFinance(
            setting_name='max_days_past',
            setting_value=max_days_past,
            description='Maximum number of days in the past for expense claims',
            updated_by=user_email,
            updated_on=datetime.now()
        )
        db.session.add(max_days_past_setting)
        db.session.commit()

        flash(f'Maximum days in past for claims set to {max_days_past}.', 'success')

    return redirect(url_for('settings'))

@app.route('/dashboard')
@login_required
def dashboard():
    # User is guaranteed to be logged in due to @login_required

    # Get employee details from session
    employee_role = session.get('employee_role')
    employee_manager = session.get('employee_manager')
    employee_id = session.get('employee_id')
    user_email = session.get('email')

    # Get user info from session for backward compatibility
    user_info = session.get('user_info', {})

    print(f"DEBUG: Dashboard accessed by {user_email}")
    print(f"DEBUG: Employee role: {employee_role}, Manager: {employee_manager}, ID: {employee_id}")

    # Get filter options
    expense_heads = ExpenseHead.query.filter_by(is_active=True).all()

    # Filter cost centers based on user role
    if employee_role in ['Finance', 'Finance Approver', 'Super Admin']:
        # Finance, Finance Approver, and Super Admin see all cost centers
        cost_centers = CostCenter.query.filter_by(is_active=True).all()
    elif session.get('is_cost_center_approver'):
        # Cost Center Approver sees only cost centers they're approvers for
        cost_centers = CostCenter.query.filter_by(approver_email=user_email, is_active=True).all()
    else:
        # Regular users see only cost centers they've submitted EPVs for
        user_cost_center_ids = db.session.query(EPV.cost_center_id).filter(EPV.email_id == user_email).distinct().all()
        user_cost_center_ids = [cc_id[0] for cc_id in user_cost_center_ids if cc_id[0] is not None]

        if user_cost_center_ids:
            cost_centers = CostCenter.query.filter(CostCenter.id.in_(user_cost_center_ids), CostCenter.is_active == True).all()
        else:
            cost_centers = []

    # Get filter values from request
    expense_head_filter = request.args.get('expense_head', '')
    cost_center_filter = request.args.get('cost_center', '')
    time_period_filter = request.args.get('time_period', 'all')
    city_filter = request.args.get('city', '')

    # Get cities for the filter dropdown (for finance users)
    cities = []
    if employee_role in ['Finance', 'Finance Approver', 'Super Admin']:
        # For Finance users, show only assigned cities
        if employee_role == 'Finance':
            # Get the employee ID from the email
            employee = EmployeeDetails.query.filter_by(email=user_email).first()
            if employee:
                # Get the city assignments for this employee
                city_assignments = CityAssignment.query.filter_by(employee_id=employee.id, is_active=True).all()
                cities = [ca.city for ca in city_assignments if ca.city]
        # For Finance Approver and Super Admin, show all cities
        else:
            # Get all unique cities from cost centers
            cities = db.session.query(CostCenter.city).distinct().filter(CostCenter.city.isnot(None)).all()
            cities = [city[0] for city in cities if city[0]]  # Extract city names and filter out None values

    # Define time period filter dates
    today = datetime.now().date()
    if time_period_filter == 'this_month':
        start_date = datetime(today.year, today.month, 1).date()
        end_date = today
    elif time_period_filter == 'last_month':
        if today.month == 1:
            start_date = datetime(today.year - 1, 12, 1).date()
            end_date = datetime(today.year, 1, 1).date() - timedelta(days=1)
        else:
            start_date = datetime(today.year, today.month - 1, 1).date()
            end_date = datetime(today.year, today.month, 1).date() - timedelta(days=1)
    elif time_period_filter == 'this_year':
        start_date = datetime(today.year, 1, 1).date()
        end_date = today
    else:  # 'all'
        start_date = None
        end_date = None

    # Get real data for scorecards
    try:
        # Base query for EPVs - Finance users see all entries, others see only their own
        if employee_role in ['Finance', 'Finance Approver', 'Super Admin']:
            # Finance users see EPVs based on their assigned cities
            if employee_role == 'Finance':
                # Get the employee ID from the email
                employee = EmployeeDetails.query.filter_by(email=user_email).first()
                if employee:
                    # Get the city assignments for this employee
                    city_assignments = CityAssignment.query.filter_by(employee_id=employee.id, is_active=True).all()
                    assigned_cities = [ca.city for ca in city_assignments if ca.city]

                    if assigned_cities:
                        # Get cost centers in the assigned cities
                        assigned_cost_center_ids = db.session.query(CostCenter.id).filter(CostCenter.city.in_(assigned_cities)).all()
                        assigned_cost_center_ids = [cc_id[0] for cc_id in assigned_cost_center_ids]

                        # Base query for EPVs in assigned cost centers
                        base_query = EPV.query.filter(EPV.cost_center_id.in_(assigned_cost_center_ids))

                        # If city filter is applied, filter by that specific city
                        if city_filter and city_filter in assigned_cities:
                            city_cost_center_ids = db.session.query(CostCenter.id).filter(CostCenter.city == city_filter).all()
                            city_cost_center_ids = [cc_id[0] for cc_id in city_cost_center_ids]

                            if city_cost_center_ids:
                                base_query = EPV.query.filter(EPV.cost_center_id.in_(city_cost_center_ids))
                    else:
                        # If no cities assigned, show no EPVs
                        base_query = EPV.query.filter(EPV.id == -1)  # This will return no results
                else:
                    # If employee not found, show no EPVs
                    base_query = EPV.query.filter(EPV.id == -1)  # This will return no results
            else:
                # Finance Approver and Super Admin see all EPVs
                base_query = EPV.query

                # If city filter is applied, filter by cost centers in that city
                if city_filter:
                    # Get cost centers in the selected city
                    city_cost_center_ids = db.session.query(CostCenter.id).filter(CostCenter.city == city_filter).all()
                    city_cost_center_ids = [cc_id[0] for cc_id in city_cost_center_ids]

                    # Filter EPVs by cost centers in the selected city
                    if city_cost_center_ids:
                        base_query = base_query.filter(EPV.cost_center_id.in_(city_cost_center_ids))
        else:
            # Regular users see only their own EPVs
            base_query = EPV.query.filter(EPV.email_id == user_email)

        # Apply filters to base query
        if expense_head_filter:
            # Join with EPVItem to filter by expense_head
            base_query = base_query.join(EPVItem, EPV.id == EPVItem.epv_id)
            base_query = base_query.filter(EPVItem.expense_head == expense_head_filter)
            # Make sure we get distinct EPVs (to avoid duplicates from the join)
            base_query = base_query.distinct()

        if cost_center_filter:
            base_query = base_query.filter(EPV.cost_center_name == cost_center_filter)

        if start_date and end_date:
            base_query = base_query.filter(EPV.submission_date.between(start_date, end_date))

        # Debug the SQL query
        print(f"DEBUG: Dashboard SQL Query: {str(base_query)}")

        # 1. Pending Claims - Count of EPVs with status 'submitted' or 'pending_approval'
        pending_query = base_query.filter(EPV.status.in_(['submitted', 'pending_approval']))
        pending_claims = pending_query.count()

        # 2. Approved This Month - Count of EPVs approved in the current month
        current_month = datetime.now().month
        current_year = datetime.now().year
        approved_this_month_query = base_query.filter(
            EPV.status == 'approved',
            db.extract('month', EPV.approved_on) == current_month,
            db.extract('year', EPV.approved_on) == current_year
        )
        approved_this_month = approved_this_month_query.count()

        # 3. Total Amount - Sum of all approved EPVs
        total_amount_query = base_query.filter(EPV.status == 'approved')
        total_amount_result = db.session.query(db.func.sum(EPV.total_amount)).filter(
            EPV.id.in_([epv.id for epv in total_amount_query])
        ).scalar()
        total_amount = total_amount_result if total_amount_result else 0

        # 4. Average Processing Time - Based on payment date and manager approval/resubmission date
        # Import the processing days calculation function
        from utils import calculate_processing_days
        from models import EPVApproval, FinanceEntry

        # Get all approved EPVs with finance entries that have payment dates
        approved_epvs_query = base_query.filter(
            EPV.status == 'approved',
            EPV.finance_status == 'processed'
        ).join(FinanceEntry).filter(FinanceEntry.payment_date.isnot(None))

        approved_epvs = approved_epvs_query.all()

        # Calculate average processing time in business days
        if approved_epvs:
            processing_days = []

            # Process all approved EPVs with finance entries
            for epv in approved_epvs:
                # Find the finance entry with payment date
                finance_entry = FinanceEntry.query.filter_by(
                    epv_id=epv.id
                ).first()

                # Calculate processing days based on EPV status (regular or resubmitted)
                if finance_entry and finance_entry.payment_date:
                    business_days = calculate_processing_days(epv, finance_entry)
                    processing_days.append(business_days)
                    print(f"DEBUG: EPV {epv.epv_id} processing days: {business_days}")

            # Calculate average if we have any valid processing times
            if processing_days:
                # Calculate average and round to whole number
                avg_processing_time = round(sum(processing_days) / len(processing_days))
                print(f"DEBUG: Average processing time: {avg_processing_time} days from {len(processing_days)} EPVs")
            else:
                avg_processing_time = 0
                print("DEBUG: No valid processing times found")

        else:
            avg_processing_time = 0
            print("DEBUG: No approved EPVs with payment dates found")

    except Exception as e:
        print(f"ERROR: Failed to get dashboard data: {str(e)}")
        pending_claims = 0
        approved_this_month = 0
        total_amount = 0
        avg_processing_time = 0

    # Format the total amount with commas for thousands - use Rs. instead of ₹ to avoid Unicode issues
    formatted_total_amount = f"Rs. {total_amount:,.2f}"

    # Prepare dashboard data
    dashboard_data = {
        'pending_claims': pending_claims,
        'approved_this_month': approved_this_month,
        'total_amount': formatted_total_amount,
        'avg_processing_time': f"{avg_processing_time} days",
        'avg_processing_days': avg_processing_time  # Add the raw number for comparison in template
    }

    # Debug output - use safe encoding for Unicode characters
    try:
        print(f"DEBUG: Dashboard data: {str(dashboard_data)}")
    except UnicodeEncodeError:
        print("DEBUG: Dashboard data: [Unicode encoding error - data contains non-ASCII characters]")

    print(f"DEBUG: Filters applied - Expense Head: {expense_head_filter}, Cost Center: {cost_center_filter}, Time Period: {time_period_filter}")

    # Get finance settings
    finance_settings = {}
    finance_settings_records = SettingsFinance.query.all()
    for setting in finance_settings_records:
        finance_settings[setting.setting_name] = setting.setting_value

    return render_template('dashboard_new.html',
                           user=user_info,
                           dashboard_data=dashboard_data,
                           expense_heads=expense_heads,
                           cost_centers=cost_centers,
                           cities=cities,
                           finance_settings=finance_settings,
                           selected_expense_head=expense_head_filter,
                           selected_cost_center=cost_center_filter,
                           selected_time_period=time_period_filter,
                           selected_city=city_filter,
                           is_finance_user=(employee_role in ['Finance', 'Finance Approver', 'Super Admin']))

@app.route('/logout')
def logout():
    # Clear entire session
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/user')
def get_user():
    user_info = session.get('user_info')
    if not user_info:
        return jsonify({'error': 'Not logged in'}), 401
    return jsonify(user_info)

# Add a route to view cost centers
@app.route('/cost-centers')
def cost_centers():
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Get employee details from session
    employee_role = session.get('employee_role')
    employee_manager = session.get('employee_manager')
    employee_id = session.get('employee_id')

    # Get all cost centers
    cost_centers = CostCenter.query.all()
    return render_template('cost_centers_new.html',
                           cost_centers=cost_centers,
                           user=user_info,
                           employee_role=employee_role,
                           employee_manager=employee_manager,
                           employee_id=employee_id)

# Add a route to add/edit cost centers
@app.route('/cost-centers/edit', defaults={'id': None}, methods=['GET', 'POST'])
@app.route('/cost-centers/<int:id>/edit', methods=['GET', 'POST'])
def edit_cost_center(id):
    from flask import request

    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Get employee details from session
    employee_role = session.get('employee_role')
    employee_manager = session.get('employee_manager')
    employee_id = session.get('employee_id')

    # Check if we're editing an existing cost center or creating a new one
    if id is None:
        # Creating a new cost center
        cost_center = CostCenter()
        is_new = True
    else:
        # Editing an existing cost center
        cost_center = CostCenter.query.get_or_404(id)
        is_new = False

    if request.method == 'POST':
        # Update or create the cost center
        if is_new:
            cost_center.costcenter = request.form.get('costcenter')
            cost_center.city = request.form.get('city')
            db.session.add(cost_center)

        # Update fields for both new and existing cost centers
        cost_center.approver_email = request.form.get('approver_email')
        cost_center.drive_id = request.form.get('drive_id')
        cost_center.is_active = 'is_active' in request.form

        db.session.commit()
        return redirect(url_for('cost_centers'))

    return render_template('edit_cost_center_new.html',
                           cost_center=cost_center,
                           is_new=is_new,
                           user=user_info,
                           employee_role=employee_role,
                           employee_manager=employee_manager,
                           employee_id=employee_id)

# Add a route to view employee details
@app.route('/employees')
def employees():
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Get employee details from session
    employee_role = session.get('employee_role')
    employee_manager = session.get('employee_manager')
    employee_id = session.get('employee_id')

    # Get all employees
    employees = EmployeeDetails.query.all()
    return render_template('employees_basic.html',
                           employees=employees,
                           user=user_info,
                           employee_role=employee_role,
                           employee_manager=employee_manager,
                           employee_id=employee_id)

# Add a route to add/edit employee details
@app.route('/employees/edit', defaults={'id': None}, methods=['GET', 'POST'])
@app.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
def edit_employee(id):
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Get employee details from session
    employee_role = session.get('employee_role')
    employee_manager = session.get('employee_manager')
    employee_id = session.get('employee_id')

    # Check if we're editing an existing employee or creating a new one
    if id is None:
        # Creating a new employee
        employee = EmployeeDetails()
        is_new = True
    else:
        # Editing an existing employee
        employee = EmployeeDetails.query.get_or_404(id)
        is_new = False

    if request.method == 'POST':
        # Update or create the employee
        employee.name = request.form.get('name')
        employee.email = request.form.get('email')  # Allow email editing for all employees
        employee.employee_id = request.form.get('employee_id')
        employee.manager = request.form.get('manager')

        # Handle manager_name field
        manager_name = request.form.get('manager_name')
        if manager_name and manager_name.strip():
            # If manager_name is provided, use it
            employee.manager_name = manager_name
        elif employee.manager:
            # If manager_name is not provided but manager email is, try to find the manager's name
            manager = EmployeeDetails.query.filter_by(email=employee.manager).first()
            if manager and manager.name:
                employee.manager_name = manager.name

        employee.role = request.form.get('role')
        employee.is_active = 'is_active' in request.form

        if is_new:
            db.session.add(employee)

        db.session.commit()
        return redirect(url_for('employees'))

    return render_template('edit_employee_new.html',
                           employee=employee,
                           is_new=is_new,
                           user=user_info,
                           employee_role=employee_role,
                           employee_manager=employee_manager,
                           employee_id=employee_id)

# Add a route to toggle cost center status
@app.route('/cost_center/<int:id>/toggle-status', methods=['POST'])
@app.route('/cost_centers/<int:id>/toggle-status', methods=['POST'])  # For backward compatibility
def toggle_cost_center_status(id):
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Not logged in'})
        return redirect(url_for('index'))

    try:
        # Get the cost center
        cost_center = CostCenter.query.get_or_404(id)

        # Toggle the status
        cost_center.is_active = not cost_center.is_active
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'is_active': cost_center.is_active})
        return redirect(url_for('cost_centers'))
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        return redirect(url_for('cost_centers'))

# Add a route to toggle employee status
@app.route('/employee/<int:id>/toggle-status', methods=['POST'])
@app.route('/employees/<int:id>/toggle-status', methods=['POST'])  # For backward compatibility
def toggle_employee_status(id):
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Not logged in'})
        return redirect(url_for('index'))

    try:
        # Get the employee
        employee = EmployeeDetails.query.get_or_404(id)

        # Toggle the status
        employee.is_active = not employee.is_active
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'is_active': employee.is_active})
        return redirect(url_for('employees'))
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        return redirect(url_for('employees'))

# Add a route to view expense heads
@app.route('/expense-heads')
def expense_heads():
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Get employee details from session
    employee_role = session.get('employee_role')
    employee_manager = session.get('employee_manager')
    employee_id = session.get('employee_id')

    # Get all expense heads
    expense_heads = ExpenseHead.query.all()
    return render_template('expense_heads.html',
                           expense_heads=expense_heads,
                           user=user_info,
                           employee_role=employee_role,
                           employee_manager=employee_manager,
                           employee_id=employee_id)

# Add a route to toggle expense head status
@app.route('/expense_head/<int:id>/toggle-status', methods=['POST'])
@app.route('/expense-heads/<int:id>/toggle-status', methods=['POST'])  # For backward compatibility
def toggle_expense_head_status(id):
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Not logged in'})
        return redirect(url_for('index'))

    try:
        # Get the expense head
        expense_head = ExpenseHead.query.get_or_404(id)

        # Toggle the status
        expense_head.is_active = not expense_head.is_active
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'is_active': expense_head.is_active})
        return redirect(url_for('expense_heads'))
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        return redirect(url_for('expense_heads'))

# Add a route to add/edit expense heads
@app.route('/expense-heads/edit', defaults={'id': None}, methods=['GET', 'POST'])
@app.route('/expense-heads/<int:id>/edit', methods=['GET', 'POST'])
def edit_expense_head(id):
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Get employee details from session
    employee_role = session.get('employee_role')
    employee_manager = session.get('employee_manager')
    employee_id = session.get('employee_id')

    # Check if we're editing an existing expense head or creating a new one
    if id is None:
        # Creating a new expense head
        expense_head = ExpenseHead()
        is_new = True
    else:
        # Editing an existing expense head
        expense_head = ExpenseHead.query.get_or_404(id)
        is_new = False

    if request.method == 'POST':
        # Update or create the expense head
        expense_head.head_name = request.form.get('head_name')
        expense_head.head_code = request.form.get('head_code')
        expense_head.description = request.form.get('description')
        expense_head.is_active = 'is_active' in request.form

        if is_new:
            db.session.add(expense_head)

        db.session.commit()
        return redirect(url_for('expense_heads'))

    return render_template('edit_expense_head.html',
                           expense_head=expense_head,
                           is_new=is_new,
                           user=user_info,
                           employee_role=employee_role,
                           employee_manager=employee_manager,
                           employee_id=employee_id)

# Add a route for system documentation
@app.route('/documentation')
@login_required
def system_documentation():
    """View for system documentation with flowcharts"""
    return render_template('system_documentation.html', user=session.get('user_info'))

# Finance Reports route (temporarily disabled)
@app.route('/finance/reports')
@login_required
def finance_reports():
    """Render the finance reports page for Finance Approvers"""
    # Temporarily disable this route for all users
    flash('The Reports feature is currently under development and will be available soon.', 'info')
    return redirect(url_for('dashboard'))

    # Original code (commented out)
    # Check if user is a Finance Approver
    # if session.get('employee_role') != 'Finance Approver':
    #     flash('You do not have permission to access this page.', 'danger')
    #     return redirect(url_for('dashboard'))

    # Get the academic year from settings_finance
    academic_year = "N/A"

    # Try to get academic_year from SettingsFinance
    academic_year_setting = SettingsFinance.query.filter_by(setting_name='academic_year').first()
    if academic_year_setting:
        academic_year = academic_year_setting.setting_value
    else:
        # If not found in settings_finance, check if there's a default value in the code
        # For now, use the current year as a fallback
        current_year = datetime.now().year
        academic_year = f"{current_year}-{current_year+1}"

    # Get all cities for the filter
    cities = db.session.query(CostCenter.city).distinct().all()
    cities = [city[0] for city in cities if city[0]]

    # Get all cost centers for the filter
    cost_centers = CostCenter.query.filter_by(is_active=True).all()

    # Get all expense heads for the filter
    expense_heads = ExpenseHead.query.filter_by(is_active=True).all()

    # Placeholder for overview data
    overview_data = {
        'total_expenses': '0',
        'total_amount': '₹0',
        'avg_amount': '₹0',
        'avg_processing_time': '0 days'
    }

    return render_template(
        'finance_reports.html',
        academic_year=academic_year,
        cities=cities,
        cost_centers=cost_centers,
        expense_heads=expense_heads,
        overview_data=overview_data
    )

# API endpoint for overview report data (temporarily disabled)
@app.route('/api/reports/overview')
@login_required
def api_reports_overview():
    """API endpoint for overview report data"""
    # Temporarily disable this endpoint
    return jsonify({'error': 'This feature is currently under development'}), 503

    # Original code (commented out)
    # Check if user is a Finance Approver
    # if session.get('employee_role') != 'Finance Approver':
    #     return jsonify({'error': 'Permission denied'}), 403

    # Get query parameters
    date_range = request.args.get('date_range', 'current_month')
    city = request.args.get('city', 'all')

    # Calculate date range
    today = datetime.now()
    start_date = None
    end_date = today

    if date_range == 'current_month':
        start_date = datetime(today.year, today.month, 1)
    elif date_range == 'last_month':
        if today.month == 1:
            start_date = datetime(today.year - 1, 12, 1)
            end_date = datetime(today.year, 1, 1) - timedelta(days=1)
        else:
            start_date = datetime(today.year, today.month - 1, 1)
            end_date = datetime(today.year, today.month, 1) - timedelta(days=1)
    elif date_range == 'current_quarter':
        quarter = (today.month - 1) // 3 + 1
        start_date = datetime(today.year, (quarter - 1) * 3 + 1, 1)
    elif date_range == 'last_quarter':
        quarter = (today.month - 1) // 3 + 1
        if quarter == 1:
            start_date = datetime(today.year - 1, 10, 1)
            end_date = datetime(today.year, 1, 1) - timedelta(days=1)
        else:
            start_date = datetime(today.year, (quarter - 2) * 3 + 1, 1)
            end_date = datetime(today.year, (quarter - 1) * 3 + 1, 1) - timedelta(days=1)
    elif date_range == 'current_year':
        start_date = datetime(today.year, 1, 1)
    elif date_range == 'custom':
        # Custom date range would be handled with additional parameters
        # For now, default to current month
        start_date = datetime(today.year, today.month, 1)

    # Base query for EPVs
    query = EPV.query.filter(
        EPV.status.in_(['Approved', 'Finance Processing', 'Finance Approval Pending', 'Processed']),
        EPV.submitted_on >= start_date,
        EPV.submitted_on <= end_date
    )

    # Filter by city if specified
    if city != 'all':
        query = query.filter(EPV.city == city)

    # Get all EPVs matching the criteria
    epvs = query.all()

    # Calculate statistics
    total_expenses = len(epvs)
    total_amount = sum(epv.total_amount for epv in epvs if epv.total_amount)
    avg_amount = total_amount / total_expenses if total_expenses > 0 else 0

    # Calculate average processing time
    from utils import calculate_processing_days
    processing_days = []
    for epv in epvs:
        if epv.status == 'Processed':
            # Get the finance entry for this EPV
            finance_entry = FinanceEntry.query.filter_by(epv_id=epv.id, status='Approved').first()
            if finance_entry and finance_entry.payment_date:
                # Get the manager approval date
                approval = EPVApproval.query.filter_by(epv_id=epv.id, approver_role='Manager', status='Approved').first()
                if approval and approval.approved_on:
                    days = calculate_processing_days(approval.approved_on, finance_entry.payment_date)
                    processing_days.append(days)

    avg_processing_time = sum(processing_days) / len(processing_days) if processing_days else 0

    # Generate monthly trend data (for the current year)
    monthly_trend = [0] * 12
    for epv in epvs:
        if epv.submitted_on.year == today.year:
            month_index = epv.submitted_on.month - 1
            monthly_trend[month_index] += epv.total_amount if epv.total_amount else 0

    # Generate category distribution data
    category_distribution = {}
    for epv in epvs:
        # Get expense items for this EPV
        items = EPVItem.query.filter_by(epv_id=epv.id).all()
        for item in items:
            # Get the expense head
            expense_head = ExpenseHead.query.get(item.expense_head_id)
            if expense_head:
                head_name = expense_head.head_name
                if head_name in category_distribution:
                    category_distribution[head_name] += item.amount
                else:
                    category_distribution[head_name] = item.amount

    # Format the category distribution for the chart
    category_labels = list(category_distribution.keys())
    category_values = list(category_distribution.values())

    # Format the response
    response = {
        'total_expenses': f"{total_expenses:,}",
        'total_amount': f"₹{total_amount:,.2f}",
        'avg_amount': f"₹{avg_amount:,.2f}",
        'avg_processing_time': f"{avg_processing_time:.1f} days",
        'monthly_trend': monthly_trend,
        'category_distribution': {
            'labels': category_labels,
            'values': category_values
        }
    }

    return jsonify(response)

# API endpoint for expense trends (temporarily disabled)
@app.route('/api/reports/expense-trends')
@login_required
def api_reports_expense_trends():
    """API endpoint for expense trends data"""
    # Temporarily disable this endpoint
    return jsonify({'error': 'This feature is currently under development'}), 503

    # Original code (commented out)
    # Check if user is a Finance Approver
    # if session.get('employee_role') != 'Finance Approver':
    #     return jsonify({'error': 'Permission denied'}), 403

    # Get query parameters
    time_period = request.args.get('time_period', 'monthly')
    expense_head = request.args.get('expense_head', 'all')

    # Calculate date ranges based on time period
    today = datetime.now()
    start_date = datetime(today.year - 1, today.month, 1)  # Default to 1 year ago

    # Base query for EPVs
    query = EPV.query.filter(
        EPV.status.in_(['Approved', 'Finance Processing', 'Finance Approval Pending', 'Processed']),
        EPV.submitted_on >= start_date
    )

    # Get all EPVs matching the criteria
    epvs = query.all()

    # Prepare data structure based on time period
    labels = []
    values = []

    if time_period == 'monthly':
        # Generate monthly labels for the past 12 months
        for i in range(12):
            month = (today.month - i - 1) % 12 + 1
            year = today.year if month <= today.month else today.year - 1
            month_name = datetime(year, month, 1).strftime('%b %Y')
            labels.insert(0, month_name)

        # Initialize values array
        values = [0] * 12

        # Calculate monthly totals
        for epv in epvs:
            # Calculate months ago
            months_ago = (today.year - epv.submitted_on.year) * 12 + (today.month - epv.submitted_on.month)
            if 0 <= months_ago < 12:
                index = 11 - months_ago

                # If filtering by expense head, only include matching items
                if expense_head != 'all':
                    # Get expense items for this EPV
                    items = EPVItem.query.filter_by(epv_id=epv.id, expense_head_id=expense_head).all()
                    for item in items:
                        values[index] += item.amount
                else:
                    values[index] += epv.total_amount if epv.total_amount else 0

    elif time_period == 'quarterly':
        # Generate quarterly labels for the past 4 quarters
        current_quarter = (today.month - 1) // 3 + 1
        for i in range(4):
            quarter = (current_quarter - i - 1) % 4 + 1
            year = today.year if quarter <= current_quarter else today.year - 1
            quarter_label = f"Q{quarter} {year}"
            labels.insert(0, quarter_label)

        # Initialize values array
        values = [0] * 4

        # Calculate quarterly totals
        for epv in epvs:
            epv_quarter = (epv.submitted_on.month - 1) // 3 + 1
            quarters_ago = (today.year - epv.submitted_on.year) * 4 + (current_quarter - epv_quarter)
            if 0 <= quarters_ago < 4:
                index = 3 - quarters_ago

                # If filtering by expense head, only include matching items
                if expense_head != 'all':
                    # Get expense items for this EPV
                    items = EPVItem.query.filter_by(epv_id=epv.id, expense_head_id=expense_head).all()
                    for item in items:
                        values[index] += item.amount
                else:
                    values[index] += epv.total_amount if epv.total_amount else 0

    elif time_period == 'yearly':
        # Generate yearly labels for the past 3 years
        for i in range(3):
            year = today.year - i
            labels.insert(0, str(year))

        # Initialize values array
        values = [0] * 3

        # Calculate yearly totals
        for epv in epvs:
            years_ago = today.year - epv.submitted_on.year
            if 0 <= years_ago < 3:
                index = 2 - years_ago

                # If filtering by expense head, only include matching items
                if expense_head != 'all':
                    # Get expense items for this EPV
                    items = EPVItem.query.filter_by(epv_id=epv.id, expense_head_id=expense_head).all()
                    for item in items:
                        values[index] += item.amount
                else:
                    values[index] += epv.total_amount if epv.total_amount else 0

    # Format the response
    response = {
        'labels': labels,
        'values': values
    }

    return jsonify(response)

# Add a route for the new expense form
@app.route('/new-expense', methods=['GET', 'POST'])
def new_expense():
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Ensure we have the Google token in session
    from flask_dance.contrib.google import google
    if google.authorized and not session.get('google_token'):
        session['google_token'] = google.token
        session['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
        session['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

    # Get employee details from session
    employee_role = session.get('employee_role')
    employee_manager = session.get('employee_manager')
    employee_id = session.get('employee_id')

    # Get all active cost centers for the dropdown
    cost_centers = CostCenter.query.filter_by(is_active=True).all()

    # Get all active employees for the autocomplete
    employees = EmployeeDetails.query.filter_by(is_active=True).all()

    # Get all active expense heads
    expense_heads = ExpenseHead.query.filter_by(is_active=True).all()

    # Handle form submission
    if request.method == 'POST':
        try:
            # Process the expense form data

            # Get form data
            employee_name = request.form.get('employee_name')  # Changed from 'employeeName' to match the form field name
            cost_center_id = request.form.get('cost_center')  # Changed from 'costCenter' to match the form field name
            cost_center_name_input = request.form.get('cost_center_name')  # Get the cost center name from the input field

            # Get cost center details for Google Drive upload
            cost_center = None
            drive_folder_id = None
            cost_center_name = None

            print(f"DEBUG: Selected cost_center_id: {cost_center_id}")
            print(f"DEBUG: Cost center name from input: {cost_center_name_input}")

            # List all cost centers and their drive IDs for debugging
            try:
                all_cost_centers = CostCenter.query.all()
                print(f"DEBUG: All cost centers in database:")
                for cc in all_cost_centers:
                    print(f"DEBUG: ID: {cc.id}, Name: {cc.costcenter}, Drive ID: {cc.drive_id}")
            except Exception as e:
                print(f"ERROR: Failed to list all cost centers: {str(e)}")

            # Process cost center information
            if cost_center_id:
                # Try to convert cost_center_id to integer
                try:
                    cost_center_id = int(cost_center_id)
                except ValueError:
                    print(f"DEBUG: cost_center_id is not an integer: {cost_center_id}")

                # Try to get the cost center by ID
                try:
                    cost_center = CostCenter.query.filter_by(id=cost_center_id).first()
                    if cost_center:
                        cost_center_name = cost_center.costcenter
                        drive_folder_id = cost_center.drive_id
                        print(f"DEBUG: Found cost center by ID: {cost_center_name}, Drive folder ID: {drive_folder_id}")
                    else:
                        print(f"DEBUG: No cost center found with ID: {cost_center_id}, using name from input")
                        cost_center_name = cost_center_name_input
                except Exception as e:
                    print(f"ERROR: Failed to get cost center by ID: {str(e)}")
                    cost_center_name = cost_center_name_input
            else:
                # No cost center ID provided, use the name from input
                print(f"DEBUG: No cost center ID provided, using name from input")
                cost_center_name = cost_center_name_input

            # If we still don't have a cost center name, use a default
            if not cost_center_name:
                cost_center_name = "Unknown Cost Center"
                print(f"WARNING: Using default cost center name: {cost_center_name}")

            # Debug request.files
            print(f"DEBUG: request.files keys: {list(request.files.keys())}")
            for key in request.files.keys():
                file = request.files[key]
                print(f"DEBUG: File key: {key}, filename: {file.filename if file else 'None'}")

            # Generate a unique EPV ID for this expense
            # Format: EPV-YYYYMMDD-COSTCENTER-XXXXXXXXXX (using full cost center name, 10 hex chars from UUID for uniqueness)
            cost_center_code = generate_cost_center_code(cost_center_name)
            epv_id = f"EPV-{datetime.now().strftime('%Y%m%d')}-{cost_center_code}-{uuid.uuid4().hex[:10].upper()}"

            # Prepare expense data structure
            expense_data = {
                'employee_id': employee_id,
                'employee_name': employee_name,
                'from_date': request.form.get('from_date'),
                'to_date': request.form.get('to_date'),
                'cost_center': cost_center_name,
                'expense_type': request.form.get('expense_type'),
                'epv_id': epv_id,
                'expenses': []
            }

            # Extract expense items from form data
            # Check if we have invoice_date[] format (new format)
            if 'invoice_date[]' in request.form:
                # Get all invoice dates
                invoice_dates = request.form.getlist('invoice_date[]')
                expense_heads = request.form.getlist('expense_head[]')
                amounts = request.form.getlist('amount[]')
                descriptions = request.form.getlist('description[]')
                split_invoices = request.form.getlist('split_invoice[]')

                print(f"DEBUG: Split invoice values: {split_invoices}")

                # Process each expense item
                for i in range(len(invoice_dates)):
                    if i < len(expense_heads) and i < len(amounts) and i < len(descriptions):
                        # Check if this is a split invoice
                        is_split = False
                        if i < len(split_invoices) and split_invoices[i] == '1':
                            is_split = True
                            print(f"DEBUG: Expense #{i+1} is marked as a split invoice")

                        expense = {
                            'invoice_date': invoice_dates[i],
                            'expense_head': expense_heads[i],
                            'amount': amounts[i],
                            'description': descriptions[i],
                            'split_invoice': is_split
                        }
                        expense_data['expenses'].append(expense)
                        print(f"DEBUG: Added expense item: {expense}")
            # Old format (expenses[i][field])
            else:
                i = 0
                while f'expenses[{i}][invoice_date]' in request.form:
                    expense = {
                        'invoice_date': request.form.get(f'expenses[{i}][invoice_date]'),
                        'expense_head': request.form.get(f'expenses[{i}][expense_head]'),
                        'amount': request.form.get(f'expenses[{i}][amount]'),
                        'description': request.form.get(f'expenses[{i}][description]'),
                        'split_invoice': request.form.get(f'expenses[{i}][split_invoice]') == '1'
                    }
                    expense_data['expenses'].append(expense)
                    i += 1

            # Calculate total amount
            total_amount = sum(float(expense['amount']) for expense in expense_data['expenses'] if expense['amount'])
            expense_data['total_amount'] = f"{total_amount:.2f}"

            # Get amount in words from form or generate it
            if 'amount_in_words' in request.form and request.form.get('amount_in_words'):
                expense_data['amount_in_words'] = request.form.get('amount_in_words')
                print(f"DEBUG: Using amount in words from form: {expense_data['amount_in_words']}")
            else:
                # Generate amount in words
                from utils import number_to_words
                expense_data['amount_in_words'] = number_to_words(total_amount)
                print(f"DEBUG: Generated amount in words: {expense_data['amount_in_words']}")

            # Identify split invoices and collect all expense indices
            split_invoice_indices = []
            all_expense_indices = []
            for i, expense in enumerate(expense_data['expenses']):
                all_expense_indices.append(i)
                if expense.get('split_invoice'):
                    split_invoice_indices.append(i)
                    print(f"DEBUG: Expense #{i+1} is marked as a split invoice, will skip receipt upload")

            # Find the highest index in the expenses
            max_expense_index = max(all_expense_indices) if all_expense_indices else -1
            print(f"DEBUG: Max expense index: {max_expense_index}")
            print(f"DEBUG: Split invoice indices: {split_invoice_indices}")

            # Check if there are any expenses after a split invoice
            has_expenses_after_split = False
            for i in all_expense_indices:
                # If this expense comes after a split invoice
                for split_idx in split_invoice_indices:
                    if i > split_idx:
                        has_expenses_after_split = True
                        print(f"DEBUG: Found expense #{i+1} after split invoice #{split_idx+1}")
                        break
                if has_expenses_after_split:
                    break

            # Process files based on split invoice information
            expense_files = []

            # Print all files for debugging
            print(f"DEBUG: All files in request.files: {list(request.files.keys())}")
            print(f"DEBUG: Split invoice indices: {split_invoice_indices}")

            # Get all receipt files
            receipt_files = request.files.getlist('receipt[]')
            print(f"DEBUG: Found {len(receipt_files)} receipt[] files")

            # Print all receipt files for debugging
            for i, file in enumerate(receipt_files):
                print(f"DEBUG: Receipt file {i}: {file.filename}")

            # Create a mapping of expense index to file
            expense_file_map = {}

            # First, map the first file to the first expense
            if len(receipt_files) > 0 and receipt_files[0].filename:
                expense_file_map[0] = receipt_files[0]
                print(f"DEBUG: Mapped first file {receipt_files[0].filename} to expense index 0")

            # Now map the remaining files to non-split expenses
            file_index = 1  # Start from the second file
            expense_index = 1  # Start from the second expense

            while file_index < len(receipt_files) and expense_index <= max_expense_index:
                # Skip split invoices
                if expense_index in split_invoice_indices:
                    print(f"DEBUG: Skipping split invoice at expense index {expense_index}")
                    expense_index += 1
                    continue

                # Map the file to the expense
                if receipt_files[file_index].filename:
                    expense_file_map[expense_index] = receipt_files[file_index]
                    print(f"DEBUG: Mapped file {receipt_files[file_index].filename} to expense index {expense_index}")
                    file_index += 1

                expense_index += 1

            # Print the final mapping
            print(f"DEBUG: Final expense to file mapping:")
            for exp_idx, file in expense_file_map.items():
                print(f"DEBUG: Expense {exp_idx} -> {file.filename}")

            # Add all files to be processed
            for exp_idx, file in expense_file_map.items():
                print(f"DEBUG: Adding file for expense {exp_idx}: {file.filename}")
                expense_files.append(file)

            # Step 1: Generate expense document PDF
            from pdf_converter import generate_expense_document, REPORTLAB_AVAILABLE
            expense_pdf_path = generate_expense_document(expense_data)

            if not expense_pdf_path:
                error_message = 'Failed to generate expense document'
                if not REPORTLAB_AVAILABLE:
                    error_message = 'ReportLab library is not available for PDF generation. Please contact your administrator.'
                return jsonify({
                    'success': False,
                    'message': error_message
                })

            # Debug print expense type
            print(f"DEBUG: expense_type from form: {request.form.get('expense_type')}")

            # Initialize variables to track file processing status
            file_url = None
            file_id = None
            merged_pdf_path = None

            # Step 2: Process the files if any were uploaded
            result = None
            if expense_files:
                try:
                    # Process the files: save, convert to PDF, merge with expense document, and upload to Google Drive
                    result = process_files(
                        files=expense_files,
                        drive_folder_id=drive_folder_id,
                        employee_name=employee_name,
                        cost_center_name=cost_center_name,
                        expense_pdf_path=expense_pdf_path
                    )

                    # Check if file processing was successful
                    if not result['success']:
                        error_msg = result.get('error') or "Failed to process files."
                        user_msg = result.get('user_message') or "There was an issue with the file processing."
                        return jsonify({
                            'success': False,
                            'message': user_msg,
                            'error': error_msg
                        })

                    # Store merged PDF path if available
                    if result.get('merged_pdf'):
                        merged_pdf_path = result['merged_pdf']
                        session['merged_pdf_path'] = merged_pdf_path

                    # Check if Google Drive upload was successful
                    if result.get('drive_file_id') and result.get('drive_file_url'):
                        file_id = result['drive_file_id']
                        file_url = result['drive_file_url']
                        print(f"File uploaded to Google Drive: {file_url}")
                    else:
                        # If Drive upload failed, return error
                        drive_error = result.get('drive_error') or "Failed to upload to Google Drive."
                        return jsonify({
                            'success': False,
                            'message': "File processing completed but Google Drive upload failed.",
                            'error': drive_error
                        })
                except Exception as e:
                    print(f"Error processing files: {str(e)}")
                    import traceback
                    print(f"DEBUG: File processing error traceback: {traceback.format_exc()}")
                    return jsonify({
                        'success': False,
                        'message': 'Error processing files.',
                        'error': str(e)
                    })
            else:
                # No files uploaded, just upload the expense document to Google Drive
                try:
                    # Generate a filename for download
                    download_filename = f"Expense_{employee_name}_{cost_center_name}_{datetime.now().strftime('%Y-%m-%d')}.pdf"

                    # If drive_folder_id is provided, upload to Google Drive
                    if drive_folder_id:
                        from drive_utils import upload_file_to_drive, get_file_url
                        file_id = upload_file_to_drive(expense_pdf_path, download_filename, drive_folder_id)

                        if file_id and file_id != 'local_file':
                            file_url = get_file_url(file_id)
                            print(f"Expense document uploaded to Google Drive: {file_url}")
                        else:
                            return jsonify({
                                'success': False,
                                'message': 'Failed to upload expense document to Google Drive'
                            })
                    else:
                        return jsonify({
                            'success': False,
                            'message': f"No Google Drive folder ID found for the selected cost center: {cost_center_name if cost_center_name else cost_center_id}"
                        })

                    # Store the PDF path in session for download
                    session['merged_pdf_path'] = expense_pdf_path
                    merged_pdf_path = expense_pdf_path
                except Exception as e:
                    print(f"Error uploading expense document: {str(e)}")
                    import traceback
                    print(f"DEBUG: Document upload error traceback: {traceback.format_exc()}")
                    return jsonify({
                        'success': False,
                        'message': f"Error uploading expense document: {str(e)}"
                    })

            # Step 3: Now that file processing and Google Drive upload are successful, save to database
            try:
                # Create new EPV record
                new_epv = EPV(
                    epv_id=epv_id,
                    email_id=session.get('email', ''),  # Capture the user's email
                    employee_name=employee_name,
                    employee_id=employee_id,
                    from_date=datetime.strptime(request.form.get('from_date'), '%Y-%m-%d'),
                    to_date=datetime.strptime(request.form.get('to_date'), '%Y-%m-%d'),
                    payment_to=request.form.get('expense_type', 'General Expense'),  # Default value if not provided
                    acknowledgement=request.form.get('acknowledgement', 'Yes') if request.form.get('acknowledgement') else None,  # Save acknowledgement
                    submission_date=datetime.now(),
                    academic_year=f"{datetime.now().year}-{datetime.now().year + 1}",
                    cost_center_id=cost_center_id,
                    cost_center_name=cost_center_name,
                    city=request.form.get('city', ''),  # Get city from the form
                    total_amount=float(expense_data['total_amount']),
                    amount_in_words=expense_data.get('amount_in_words', ''),
                    status='submitted',
                    file_url=file_url,  # Add the Google Drive file URL
                    drive_file_id=file_id  # Add the Google Drive file ID
                )

                db.session.add(new_epv)
                db.session.flush()  # Get the ID without committing

                # Add expense items
                for expense in expense_data['expenses']:
                    item = EPVItem(
                        epv_id=new_epv.id,
                        expense_invoice_date=datetime.strptime(expense['invoice_date'], '%Y-%m-%d'),
                        expense_head=expense['expense_head'],
                        description=expense['description'],
                        amount=float(expense['amount']),
                        gst=0.0,  # Default value, can be updated later
                        split_invoice=expense.get('split_invoice', False)  # Include the split invoice flag
                    )
                    db.session.add(item)

                db.session.commit()
                print(f"DEBUG: Saved expense data to database with EPV ID: {epv_id}")
                print(f"DEBUG: EPV record ID: {new_epv.id}")
            except Exception as e:
                db.session.rollback()
                print(f"ERROR saving expense data to database: {str(e)}")
                import traceback
                print(f"DEBUG: Database error traceback: {traceback.format_exc()}")
                return jsonify({
                    'success': False,
                    'message': 'File processing and upload successful, but database save failed.',
                    'error': str(e)
                })

            # Store success response for later
            success_response = {
                'success': True,
                'message': 'Expense submitted successfully!',
                'epv_id': epv_id,
                'pdf_url': '/download-pdf'
            }

            # Add drive file URL to response if available
            if file_url:
                success_response['drive_file_url'] = file_url

            print("DEBUG: About to create approval record")
            print(f"DEBUG: Current session data: {session}")

            # Get manager email for approval - but don't send email automatically
            # The email will be sent when the user clicks the "Send for Approval" button
            manager_email = session.get('employee_manager', '')
            print(f"DEBUG: Manager email from session: {manager_email}")

            # Add manager email to the response
            success_response['manager_email'] = manager_email

            # No need for additional code here, approval record is created above

            # Return success
            return jsonify(success_response)
        except Exception as e:
            print(f"Unexpected error in expense submission: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error submitting expense.',
                'error': str(e)
            }), 500

    # For GET requests, render the form
    return render_template('new_expense.html',
                           user=user_info,
                           employee_role=employee_role,
                           employee_manager=employee_manager,
                           employee_id=employee_id,
                           cost_centers=cost_centers,
                           employees=employees,
                           expense_heads=expense_heads)

@app.route('/split-invoice-allocation', methods=['GET', 'POST'])
def split_invoice_allocation():
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Handle form submission
    if request.method == 'POST':
        # Wrap the entire function in a try-except block
        try:
            # Get master invoice details
            master_invoice_amount = float(request.form.get('master_invoice_amount'))
            master_invoice_date = datetime.strptime(request.form.get('master_invoice_date'), '%Y-%m-%d') if request.form.get('master_invoice_date') else datetime.now()
            master_invoice_description = request.form.get('master_invoice_description')

            # Generate EPV ID for master invoice
            # For master invoices, use "MASTER" as the cost center code
            epv_id = f"EPV-{datetime.now().strftime('%Y%m%d')}-MASTER-{uuid.uuid4().hex[:10].upper()}"

            # Check if we're using a previously uploaded file
            if request.form.get('master_invoice_file') == 'already_uploaded':
                # Get the file from the session
                if 'merged_pdf_path' not in session:
                    flash('No file information found in session. Please go back to the expense form and try again.', 'error')
                    return redirect(url_for('new_expense'))

                # Use the file path from the session
                pdf_path = session['merged_pdf_path']
                print(f"DEBUG: Using previously uploaded file: {pdf_path}")

                # Get the invoice date from the session or form
                if not request.form.get('master_invoice_date') or request.form.get('master_invoice_date') == '':
                    # Try to get the invoice date from the session
                    if 'expense_invoice_date' in session:
                        master_invoice_date = datetime.strptime(session['expense_invoice_date'], '%Y-%m-%d')
                        print(f"DEBUG: Using invoice date from session: {master_invoice_date}")
                    else:
                        # Default to today if no date is found
                        master_invoice_date = datetime.now()
                        print(f"DEBUG: Using today's date as invoice date: {master_invoice_date}")

                # Skip file processing steps since we already have the file
            else:
                # Process the uploaded file
                if 'master_invoice_file' not in request.files:
                    flash('No file uploaded', 'error')
                    return redirect(request.url)

                file = request.files['master_invoice_file']
                if file.filename == '':
                    flash('No file selected', 'error')
                    return redirect(request.url)

                # Create a temporary directory for file processing
                import tempfile
                temp_dir = tempfile.mkdtemp()

                # Save the uploaded file
                from werkzeug.utils import secure_filename
                file_path = os.path.join(temp_dir, secure_filename(file.filename))
                file.save(file_path)

                # Convert to PDF if needed
                from pdf_converter import convert_to_pdf
                pdf_path = convert_to_pdf(file_path)
                if not pdf_path:
                    flash('Error converting file to PDF', 'error')
                    return redirect(request.url)

            # Process the file (convert to PDF, upload to Google Drive, etc.)
            from_date = master_invoice_date
            to_date = master_invoice_date

            # If we're using a previously uploaded file, we can skip some steps
            if request.form.get('master_invoice_file') == 'already_uploaded':
                # Use the merged PDF path from the session
                merged_pdf_path = pdf_path

                # Generate amount in words for the database record
                from utils import number_to_words
                expense_amount_in_words = number_to_words(master_invoice_amount)
            else:
                # We already created the temp directory and file above
                # Convert to PDF if needed
                pdf_path = file_path
                if not file_path.lower().endswith('.pdf'):
                    try:
                        from pdf_converter import convert_to_pdf
                        pdf_path = convert_to_pdf(file_path)
                    except Exception as e:
                        print(f"Error converting file to PDF: {str(e)}")
                        flash(f"Error converting file to PDF: {str(e)}", 'error')
                        return redirect(request.url)

                # Generate the expense document PDF
                # Create a temporary data structure for the expense document
                expense_data = {
                    'employee_name': user_info.get('name', ''),
                    'employee_id': session.get('employee_id', ''),
                    'from_date': from_date,
                    'to_date': to_date,
                    'epv_id': epv_id,
                    'total_amount': master_invoice_amount,
                    'expenses': [{
                        'invoice_date': master_invoice_date.strftime('%Y-%m-%d'),
                        'expense_head': 'Split Invoice',
                        'description': master_invoice_description,
                        'amount': master_invoice_amount
                    }]
                }

                # Generate amount in words
                from utils import number_to_words
                expense_data['amount_in_words'] = number_to_words(master_invoice_amount)
                expense_amount_in_words = expense_data['amount_in_words']

                try:
                    # Generate the expense document PDF
                    from pdf_converter import generate_expense_document
                    expense_doc_path = generate_expense_document(expense_data)
                    if not expense_doc_path:
                        raise Exception("Failed to generate expense document")

                    # Merge the expense document with the invoice PDF
                    from pdf_converter import merge_pdfs
                    # The merge_pdfs function returns the path to the merged PDF
                    merged_pdf_path = merge_pdfs([expense_doc_path, pdf_path])
                    if not merged_pdf_path:
                        raise Exception("Failed to merge PDFs")
                except Exception as e:
                    print(f"Error processing PDF: {str(e)}")
                    flash(f"Error processing PDF: {str(e)}", 'error')
                    return redirect(request.url)

                # Upload to Google Drive
                # For this demo, we'll skip the actual Google Drive upload
                # In a production environment, you would upload the file to Google Drive
                # and get the file URL and ID
                file_url = f"/download-file/{epv_id}"
                file_id = f"demo_file_id_{epv_id}"

                print(f"DEBUG: File would be uploaded to Google Drive with ID {file_id}")

                # Create master invoice record
                # Get the amount in words
                from utils import number_to_words
                if request.form.get('master_invoice_file') == 'already_uploaded':
                    amount_in_words_text = expense_amount_in_words
                else:
                    amount_in_words_text = expense_data['amount_in_words']

                master_invoice = EPV(
                    epv_id=epv_id,
                    email_id=session.get('email', ''),
                    employee_name=user_info.get('name', ''),
                    employee_id=session.get('employee_id', ''),
                    from_date=from_date,
                    to_date=to_date,
                    payment_to='Vendor',
                    submission_date=datetime.now(),
                    academic_year=f"{datetime.now().year}-{datetime.now().year + 1}",
                    total_amount=master_invoice_amount,
                    amount_in_words=amount_in_words_text,
                    status='submitted',
                    file_url=file_url,
                    drive_file_id=file_id,
                    invoice_type='master',
                    split_status='splitting',
                    cost_center_name='Master Invoice'  # Add this to prevent NULL error
                )

                print(f"DEBUG: Created master invoice with EPV ID {epv_id}")

                db.session.add(master_invoice)
                db.session.flush()  # Get the ID without committing

                # Add master expense item
                master_item = EPVItem(
                    epv_id=master_invoice.id,
                    expense_invoice_date=master_invoice_date,
                    expense_head='Split Invoice',
                    description=master_invoice_description,
                    amount=master_invoice_amount,
                    gst=0.0
                )
                db.session.add(master_item)

                # Process allocations
                allocation_index = 0

                # Debug: Print all form data
                print("DEBUG: Form data:")
                for key, value in request.form.items():
                    print(f"DEBUG: {key} = {value}")

                while f'allocations[{allocation_index}][cost_center_id]' in request.form or f'allocations[{allocation_index}][cost_center_name]' in request.form:
                    cost_center_id = request.form.get(f'allocations[{allocation_index}][cost_center_id]')
                    cost_center_name = request.form.get(f'allocations[{allocation_index}][cost_center_name]')

                    print(f"DEBUG: Processing allocation #{allocation_index+1} with cost_center_id = {cost_center_id}, cost_center_name = {cost_center_name}")

                    # Try to get the cost center by ID first
                    cost_center = None
                    if cost_center_id:
                        cost_center = CostCenter.query.get(cost_center_id)
                        if cost_center:
                            print(f"DEBUG: Found cost center by ID: {cost_center.id}, name: {cost_center.costcenter}")

                    # If not found by ID, try by costcenter field
                    if not cost_center and cost_center_name:
                        print(f"DEBUG: Trying to find cost center by costcenter field: {cost_center_name}")
                        cost_center = CostCenter.query.filter_by(costcenter=cost_center_name).first()

                        if cost_center:
                            print(f"DEBUG: Found cost center by costcenter field: {cost_center.costcenter} with ID: {cost_center.id}")
                            # Update the cost_center_id for later use
                            cost_center_id = cost_center.id

                    # If still not found, try a partial match on the costcenter field
                    if not cost_center and cost_center_name:
                        print(f"DEBUG: Trying partial match for cost center costcenter field: {cost_center_name}")
                        cost_centers = CostCenter.query.filter(CostCenter.costcenter.like(f"%{cost_center_name}%")).all()
                        if cost_centers:
                            # Use the first match
                            cost_center = cost_centers[0]
                            print(f"DEBUG: Found cost center by partial match: {cost_center.costcenter} with ID: {cost_center.id}")
                            # Update the cost_center_id for later use
                            cost_center_id = cost_center.id

                    if not cost_center:
                        flash(f"Cost center not found for allocation #{allocation_index+1}", 'error')
                        return redirect(request.url)

                    allocation_amount = float(request.form.get(f'allocations[{allocation_index}][amount]'))
                    allocation_description = request.form.get(f'allocations[{allocation_index}][description]')

                    # Create sub-invoice record
                    # Generate distinctive cost center code for sub-invoice
                    cost_center_code = generate_cost_center_code(cost_center.costcenter)
                    sub_epv_id = f"EPV-{datetime.now().strftime('%Y%m%d')}-{cost_center_code}-{uuid.uuid4().hex[:10].upper()}"
                    sub_invoice = EPV(
                        epv_id=sub_epv_id,
                        email_id=session.get('email', ''),
                        employee_name=user_info.get('name', ''),
                        employee_id=session.get('employee_id', ''),
                        from_date=from_date,
                        to_date=to_date,
                        payment_to='Vendor',
                        submission_date=datetime.now(),
                        academic_year=f"{datetime.now().year}-{datetime.now().year + 1}",
                        cost_center_id=cost_center_id,
                        cost_center_name=cost_center.costcenter,
                        total_amount=allocation_amount,
                        amount_in_words=number_to_words(allocation_amount),
                        status='submitted',
                        file_url=file_url,
                        drive_file_id=file_id,
                        invoice_type='sub',
                        master_invoice_id=master_invoice.id
                    )

                    db.session.add(sub_invoice)
                    db.session.flush()  # Get the ID without committing

                    # Add sub-invoice expense item
                    sub_item = EPVItem(
                        epv_id=sub_invoice.id,
                        expense_invoice_date=master_invoice_date,
                        expense_head='Split Invoice Allocation',
                        description=allocation_description,
                        amount=allocation_amount,
                        gst=0.0
                    )
                    db.session.add(sub_item)

                    # Get the approver email from the form
                    approver_email = request.form.get(f'allocations[{allocation_index}][approver_email]')

                    if approver_email:
                        # Create an approval record for the specified approver
                        # Generate a unique token for this approval
                        token = str(uuid.uuid4())

                        # Get approver name from employee_details
                        approver_name = None
                        approver = EmployeeDetails.query.filter_by(email=approver_email).first()
                        if approver:
                            approver_name = approver.name

                        # Create an EPVApproval record
                        approval = EPVApproval(
                            epv_id=sub_invoice.id,
                            approver_email=approver_email,
                            approver_name=approver_name,
                            status='pending',
                            token=token
                        )
                        db.session.add(approval)

                    allocation_index += 1

                # Update master invoice status
                master_invoice.split_status = 'pending_approval'

                # Refresh the master invoice to ensure relationships are loaded
                db.session.refresh(master_invoice)

                # Commit all changes
                db.session.commit()

                # Send approval emails for each sub-invoice
                sent_emails = 0
                total_approvals = 0

                # Get all sub-invoices
                sub_invoices = EPV.query.filter_by(master_invoice_id=master_invoice.id).all()
                print(f"DEBUG: Found {len(sub_invoices)} sub-invoices for master invoice {master_invoice.epv_id}")

                for sub_invoice in sub_invoices:
                    # Get approvals for this sub-invoice
                    approvals = EPVApproval.query.filter_by(epv_id=sub_invoice.id).all()
                    print(f"DEBUG: Found {len(approvals)} approvals for sub-invoice {sub_invoice.epv_id}")

                    for approval in approvals:
                        total_approvals += 1
                        try:
                            # Send approval email

                            # Send the email
                            print(f"DEBUG: Attempting to send approval email to {approval.approver_email} for {sub_invoice.epv_id}")
                            try:
                                # Get Google credentials from session
                                credentials = None
                                if 'google_token' in session:
                                    try:
                                        token_info = session['google_token']
                                        # Create credentials object
                                        credentials = Credentials(
                                            token=token_info.get('access_token'),
                                            refresh_token=token_info.get('refresh_token'),
                                            token_uri='https://oauth2.googleapis.com/token',
                                            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                                            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
                                            scopes=['https://www.googleapis.com/auth/gmail.send']
                                        )
                                        print(f"DEBUG: Successfully created credentials with token: {token_info.get('access_token')[:10]}... (truncated)")
                                    except Exception as cred_error:
                                        print(f"DEBUG: Error creating credentials: {str(cred_error)}")

                                # Get base URL for approval links
                                if request.host.startswith('127.0.0.1') or request.host.startswith('localhost'):
                                    base_url = f"http://{request.host}"
                                else:
                                    base_url = f"https://{request.host}"

                                # Send the approval email with the token
                                from email_utils import send_approval_email as send_email
                                success, message_id = send_email(sub_invoice, approval.approver_email, credentials, base_url, approval.token)

                                if success:
                                    sent_emails += 1
                                    print(f"DEBUG: SUCCESS - Approval email sent to {approval.approver_email} for {sub_invoice.epv_id}")
                                else:
                                    print(f"DEBUG: ERROR - Failed to send approval email to {approval.approver_email}: {message_id}")
                            except Exception as email_error:
                                print(f"DEBUG: ERROR - Failed to send approval email to {approval.approver_email}: {str(email_error)}")
                        except Exception as e:
                            print(f"Error sending approval email to {approval.approver_email}: {str(e)}")

                # Create success message with email sending details
                if sent_emails == total_approvals:
                    flash(f'Split invoice created successfully! Approval emails sent to all {sent_emails} approvers.', 'success')
                elif sent_emails > 0:
                    flash(f'Split invoice created successfully! {sent_emails} out of {total_approvals} approval emails were sent.', 'success')
                else:
                    flash('Split invoice created successfully, but there was an issue sending approval emails. Please contact the approvers directly.', 'warning')

                # Redirect to the EPV records page
                return redirect(url_for('epv_records'))

        except Exception as e:
            db.session.rollback()
            import traceback
            print(f"Error creating split invoice: {str(e)}")
            print(traceback.format_exc())
            flash(f"Error creating split invoice: {str(e)}", 'error')
            return redirect(request.url)



    # GET request - render the allocation form
    return render_template('split_invoice_allocation.html')

# Add an API endpoint to get employee details
@app.route('/api/employees')
def get_employees():
    # Get search term from request
    search_term = request.args.get('term', '')

    # If search term is provided, filter employees by name
    if search_term:
        # Search for employees whose name contains the search term (case-insensitive)
        employees = EmployeeDetails.query.filter(
            EmployeeDetails.name.ilike(f'%{search_term}%'),
            EmployeeDetails.is_active == True
        ).all()
    else:
        # Get all active employees
        employees = EmployeeDetails.query.filter_by(is_active=True).all()

    # Convert to JSON
    employee_list = [{
        'id': emp.id,
        'name': emp.name,
        'email': emp.email,
        'employee_id': emp.employee_id,
        'manager': emp.manager,
        'value': emp.name,  # For jQuery UI autocomplete
        'label': f"{emp.name} ({emp.employee_id})" if emp.employee_id else emp.name  # Include employee ID in label
    } for emp in employees if emp.name]

    print(f"API response for '{search_term}': {len(employee_list)} employees found")

    return jsonify(employee_list)

# Add an API endpoint to get finance settings
@app.route('/api/settings/finance')
def get_finance_settings():
    # Get all finance settings
    settings = SettingsFinance.query.all()

    # Convert to JSON
    settings_dict = {}
    for setting in settings:
        settings_dict[setting.setting_name] = {
            'value': setting.setting_value,
            'description': setting.description
        }

    # For backward compatibility, if days is requested but max_days_past exists
    if 'days' in request.args and 'max_days_past' in settings_dict and 'days' not in settings_dict:
        settings_dict['days'] = settings_dict['max_days_past']

    return jsonify(settings_dict)

# Add an API endpoint to get notifications
@app.route('/api/notifications')
@login_required
def get_notifications():
    """Get notifications for the current user"""
    notifications = []
    user_email = session.get('email')

    # Get pending approval notifications
    if user_email:
        # Check if user is an approver for any pending expenses
        pending_approvals_query = db.session.query(EPVApproval).filter(
            EPVApproval.approver_email == user_email,
            EPVApproval.status == 'pending'
        )

        # Get the count and add notification if there are pending approvals
        if pending_approvals_query.count() > 0:
            notifications.append({
                'type': 'approval',
                'message': f'You have expenses pending your approval',
                'href': '/epv-records?status=pending_approval',
                'icon': 'fa-file-signature'
            })

        # For testing purposes, add another notification
        notifications.append({
            'type': 'pending_approval',
            'message': 'You have 3 expenses pending approval',
            'href': '/epv-records?status=pending_approval',
            'icon': 'fa-clock'
        })

        # Add another test notification
        notifications.append({
            'type': 'finance_pending',
            'message': 'You have 2 expenses to process',
            'href': '/finance-dashboard',
            'icon': 'fa-file-invoice-dollar'
        })

    # Get finance notifications for finance users
    if session.get('employee_role') in ['Finance', 'Finance Approver']:
        # Get assigned cities
        assigned_cities = []
        if session.get('employee_role') == 'Finance':
            # First get the employee ID from the email
            employee = EmployeeDetails.query.filter_by(email=user_email).first()
            if employee:
                # Then get the city assignments for this employee
                city_assignments = CityAssignment.query.filter_by(employee_id=employee.id, is_active=True).all()
                assigned_cities = [ca.city for ca in city_assignments]

        # For Finance Approver, show all cities
        if session.get('employee_role') == 'Finance Approver':
            # Get all expenses pending finance approval
            pending_finance_approval = db.session.query(EPV).join(
                FinanceEntry, EPV.id == FinanceEntry.epv_id
            ).filter(
                EPV.finance_status == 'processed',
                FinanceEntry.status == 'pending'
            ).count()

            if pending_finance_approval > 0:
                notifications.append({
                    'type': 'finance_approval',
                    'message': f'You have {pending_finance_approval} expenses pending finance approval',
                    'href': '/finance-dashboard?tab=for_approval',
                    'icon': 'fa-file-invoice-dollar'
                })

        # For Finance users, show expenses for their assigned cities
        elif assigned_cities:
            # Get expenses pending finance processing for assigned cities
            # Only count expenses with direct city match to assigned cities
            direct_city_count = db.session.query(EPV).filter(
                EPV.status == 'approved',
                EPV.finance_status == 'pending',
                EPV.city.in_(assigned_cities)
            ).count()

            # Then count expenses without city but with cost center city match
            cost_center_city_count = db.session.query(EPV).join(
                CostCenter, EPV.cost_center_id == CostCenter.id
            ).filter(
                EPV.status == 'approved',
                EPV.finance_status == 'pending',
                EPV.city == None,  # Only count expenses without a direct city
                CostCenter.city.in_(assigned_cities)
            ).count()

            # Total count
            pending_finance = direct_city_count + cost_center_city_count

            if pending_finance > 0:
                notifications.append({
                    'type': 'finance_pending',
                    'message': f'You have {pending_finance} expenses to process',
                    'href': '/finance-dashboard',
                    'icon': 'fa-file-invoice-dollar'
                })

    return jsonify(notifications)

# Add an API endpoint to get cost centers
@app.route('/api/cost-centers')
def get_cost_centers():
    # Get search term from request
    search_term = request.args.get('term', '')

    # If search term is provided, filter cost centers by name
    if search_term:
        # Search for cost centers whose name contains the search term (case-insensitive)
        cost_centers = CostCenter.query.filter(
            CostCenter.costcenter.ilike(f'%{search_term}%'),
            CostCenter.is_active == True
        ).all()
    else:
        # Get all active cost centers
        cost_centers = CostCenter.query.filter_by(is_active=True).all()

    # Convert to JSON
    cost_center_list = [{
        'id': cc.id,
        'name': cc.costcenter,
        'city': cc.city,
        'value': cc.costcenter,  # For jQuery UI autocomplete
        'label': cc.costcenter   # For jQuery UI autocomplete
    } for cc in cost_centers]

    print(f"API response for cost centers '{search_term}': {len(cost_center_list)} found")

    return jsonify(cost_center_list)

# Add a route to download the merged PDF
@app.route('/download-pdf')
def download_pdf():
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Get the PDF path from session
    pdf_path = session.get('merged_pdf_path')
    if not pdf_path:
        return jsonify({'error': 'No PDF file available'}), 404

    # Check if the file exists
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'PDF file not found'}), 404

    # Return the file for download
    try:
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name='expense_receipts.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")
        return jsonify({'error': f'Error downloading PDF: {str(e)}'}), 500

# Add a route for Finance to request additional documents
@app.route('/request-documents/<epv_id>', methods=['GET', 'POST'])
@login_required
def request_documents(epv_id):
    # Import request from flask
    from flask import request

    # Check if user has Finance role
    if session.get('employee_role') not in ['Finance', 'Finance Approver', 'Super Admin']:
        flash('You do not have permission to request additional documents.', 'error')
        return redirect(url_for('dashboard'))

    # Get the EPV record
    epv = EPV.query.filter_by(epv_id=epv_id).first_or_404()

    if request.method == 'POST':
        # Get the requested documents from the form
        requested_docs = request.form.get('requested_documents')

        if not requested_docs:
            flash('Please specify what documents are missing.', 'error')
            return redirect(url_for('request_documents', epv_id=epv_id))

        # Update the EPV record
        epv.document_status = 'pending_additional_documents'
        epv.requested_documents = requested_docs

        # Update finance status - this is critical for the workflow
        epv.finance_status = 'pending_documents'

        # Always set the status to 'rejected' to ensure proper workflow
        # This will be changed back to 'approved' when documents are uploaded
        epv.status = 'rejected'

        # Print debug information
        print(f"Updated EPV status for document request: document_status={epv.document_status}, finance_status={epv.finance_status}, status={epv.status}")

        # Add a rejection with a special status
        rejection = EPVApproval(
            epv_id=epv.id,
            approver_email=session.get('email'),
            approver_name=session.get('employee_name'),
            status='documents_requested',
            action_date=datetime.now(),
            comments=f"Additional documents requested: {requested_docs}"
        )
        db.session.add(rejection)

        # Save changes
        db.session.commit()

        # Send email notification to the user
        try:
            send_document_request_email(epv, requested_docs)
            flash('Document request sent successfully.', 'success')
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            flash('Document request saved, but email notification failed.', 'warning')

        return redirect(url_for('epv_record', epv_id=epv_id))

    # GET request - show the form
    return render_template('request_documents.html', epv=epv)

# Add a route for users to upload supplementary documents
@app.route('/upload-supplementary/<epv_id>', methods=['GET', 'POST'])
@login_required
def upload_supplementary(epv_id):
    # Import request from flask
    from flask import request

    # Get the EPV record
    epv = EPV.query.filter_by(epv_id=epv_id).first_or_404()

    # Check if the user has permission to upload documents for this EPV
    user_email = session.get('email')

    # Only the original submitter or finance/admin users can upload supplementary documents
    if epv.email_id != user_email and session.get('employee_role') not in ['Finance', 'Finance Approver', 'Super Admin']:
        flash('You do not have permission to upload documents for this EPV.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Check if any files were uploaded
        uploaded_files = []

        # Process all uploaded files (both the main document and any additional ones)
        for key in request.files:
            if key.startswith('document'):
                file = request.files[key]

                # Skip empty files
                if file.filename == '':
                    continue

                # Get the corresponding description
                description_key = 'description' + key[8:] if key != 'document' else 'description'
                description = request.form.get(description_key, '')

                # Save the file
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                random_hex = uuid.uuid4().hex[:8]
                safe_filename = f"{timestamp}_{random_hex}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
                file.save(file_path)
                print(f"Saved supplementary file to: {file_path}")

                # Create a new supplementary document record
                supplementary_doc = SupplementaryDocument(
                    epv_id=epv.id,
                    filename=filename,
                    file_path=file_path,
                    uploaded_by=user_email,
                    description=description
                )
                db.session.add(supplementary_doc)

                # Add to our list of uploaded files
                uploaded_files.append((filename, file_path))

        # Check if we have any uploaded files
        if not uploaded_files:
            flash('No files were uploaded', 'error')
            return redirect(request.url)

        # Get the cost center for the folder ID
        cost_center = CostCenter.query.get(epv.cost_center_id)
        folder_id = None
        if cost_center and cost_center.drive_id:
            folder_id = cost_center.drive_id

        # Import our PDF utilities
        from pdf_utils import merge_supplementary_documents, upload_to_drive

        # Merge all supplementary documents with the original PDF
        merged_pdf_path = merge_supplementary_documents(epv, uploaded_files, app.config['UPLOAD_FOLDER'])

        if merged_pdf_path:
            print(f"Successfully merged PDFs: {merged_pdf_path}")

            # Upload the merged PDF to Google Drive
            if folder_id:
                # Upload to Google Drive
                file_name = f"Expense_{epv.employee_name}_{cost_center.costcenter if cost_center else 'Unknown'}_{datetime.now().strftime('%Y-%m-%d')}_supplementary.pdf"

                # Store the old file ID for potential deletion later
                old_file_id = epv.drive_file_id

                # Upload the new merged file
                new_file_id = upload_to_drive(merged_pdf_path, file_name, folder_id)

                if new_file_id:
                    # Update the supplementary document record for the last uploaded document
                    # (We can't update all of them since the drive_file_id field only stores one ID)
                    if uploaded_files:
                        last_doc = SupplementaryDocument.query.filter_by(
                            epv_id=epv.id,
                            file_path=uploaded_files[-1][1]
                        ).first()
                        if last_doc:
                            last_doc.drive_file_id = new_file_id

                    # Update the EPV record with the new file ID
                    epv.drive_file_id = new_file_id
                    epv.file_url = f"https://drive.google.com/file/d/{new_file_id}/view?usp=drivesdk"
                    print(f"Updated EPV record with new file ID: {new_file_id}")
                else:
                    print("Failed to upload merged PDF to Google Drive")
                    flash('Documents uploaded but could not be uploaded to Google Drive.', 'warning')
        else:
            print("Failed to merge PDFs")
            flash('Documents uploaded but could not be merged with the original PDF.', 'warning')

        # Update the EPV status regardless of whether PDF merge succeeded or failed
        # This ensures it always goes back to Finance for review
        epv.document_status = 'documents_uploaded'

        # Update the finance status to pending for review
        # This is critical for showing it in the finance dashboard
        epv.finance_status = 'pending'

        # Make sure the status is 'approved' so it shows up in the finance dashboard
        # This is critical because the finance dashboard only shows EPVs with status='approved'
        epv.status = 'approved'

        # Add a system approval record to track this status change
        system_approval = EPVApproval(
            epv_id=epv.id,
            approver_email='system@webapporbit.com',
            approver_name='System',
            status='resubmitted',
            action_date=datetime.now(),
            comments=f"Supplementary documents uploaded. EPV resubmitted to Finance for review."
        )
        db.session.add(system_approval)

        # Print debug information
        print(f"Updated EPV status: document_status={epv.document_status}, finance_status={epv.finance_status}, status={epv.status}")

        # Save changes
        db.session.commit()

        # Notify finance team
        try:
            # Get all finance users
            finance_users = EmployeeDetails.query.filter(
                EmployeeDetails.role.in_(['Finance', 'Finance Approver'])
            ).all()

            # Send notification to each finance user
            for finance_user in finance_users:
                send_email(
                    to=finance_user.email,
                    subject=f"Supplementary Documents Uploaded: {epv.epv_id}",
                    html_content=render_template(
                        'email/supplementary_notification.html',
                        epv=epv,
                        finance_user=finance_user,
                        base_url=request.url_root.rstrip('/')
                    )
                )
            print(f"Sent notifications to {len(finance_users)} finance users")
        except Exception as e:
            print(f"Error notifying finance team: {str(e)}")

        flash('Supplementary documents uploaded and merged successfully. The expense has been sent to Finance for review.', 'success')
        return redirect(url_for('epv_records'))

    # GET request - show the form
    return render_template('upload_supplementary.html', epv=epv)

# Add a route to download a file for a specific EPV record
@app.route('/download-file/<epv_id>')
def download_file(epv_id):
    # Check if user is logged in
    if 'email' not in session:
        return redirect(url_for('login'))

    # Get the EPV record
    epv = EPV.query.filter_by(epv_id=epv_id).first_or_404()

    # Check if the user has permission to view this record
    user_email = session.get('email')
    employee = EmployeeDetails.query.filter_by(email=user_email).first()
    role = employee.role if employee else 'user'

    if role != 'Super Admin' and epv.email_id != user_email:
        print(f"DEBUG: Access denied for user {user_email} to download file for EPV {epv_id}")
        return redirect(url_for('epv_records'))

    # Try to get the file path
    file_path = None

    # First, try to find the file in the local file system
    pdf_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf_uploads')

    # Check if there's a file with the EPV ID in its name
    for filename in os.listdir(pdf_dir):
        if epv_id.lower() in filename.lower():
            file_path = os.path.join(pdf_dir, filename)
            print(f"Found file in pdf_uploads directory with EPV ID in name: {file_path}")
            break

    # If no file with EPV ID in name, check if there's a merged PDF file
    if not file_path:
        # Get the most recent merged PDF file
        merged_files = [f for f in os.listdir(pdf_dir) if f.startswith('merged_')]
        if merged_files:
            # Sort by modification time (most recent first)
            merged_files.sort(key=lambda x: os.path.getmtime(os.path.join(pdf_dir, x)), reverse=True)
            file_path = os.path.join(pdf_dir, merged_files[0])
            print(f"Using most recent merged PDF file: {file_path}")

    # If we couldn't find the file locally and the EPV has a drive_file_id, try to download from Google Drive
    if (not file_path or not os.path.exists(file_path)) and epv.drive_file_id and epv.drive_file_id != f"demo_file_id_{epv_id}":
        try:
            # Import Google Drive utilities
            from drive_utils import download_file_from_drive

            # Create a temporary file to store the downloaded content
            import tempfile
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, f"{epv_id}.pdf")

            # Download the file from Google Drive
            print(f"Attempting to download file from Google Drive with ID: {epv.drive_file_id}")
            success = download_file_from_drive(epv.drive_file_id, temp_file)
            if success:
                file_path = temp_file
                print(f"Successfully downloaded file from Google Drive: {file_path}")
        except Exception as e:
            print(f"Error downloading file from Google Drive: {str(e)}")

    # If we still don't have a file path, return an error
    if not file_path or not os.path.exists(file_path):
        return render_template('error.html', error="File not found"), 404

    # Return the file for download
    try:
        return send_file(
            file_path,
            as_attachment=False,  # Display in browser by default
            download_name=f"expense_{epv_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return render_template('error.html', error=f"Error downloading file: {str(e)}"), 500

# Add an API endpoint to get expense heads
@app.route('/api/expense-heads')
def get_expense_heads():
    # Get all active expense heads
    expense_heads = ExpenseHead.query.filter_by(is_active=True).all()

    # Convert to JSON
    expense_head_list = [{
        'id': head.id,
        'head_name': head.head_name,
        'head_code': head.head_code,
        'description': head.description
    } for head in expense_heads]

    return jsonify(expense_head_list)

# Add a route to reset the database (for development only)
@app.route('/reset-db')
def reset_db():
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Drop all tables and recreate them
    with app.app_context():
        db.drop_all()
        db.create_all()
        init_db(app)

    return redirect(url_for('dashboard'))

# Add a route to view settings (for development only)
@app.route('/view-settings')
def view_settings():
    # Check if user is logged in
    user_info = session.get('user_info')
    if not user_info:
        return redirect(url_for('index'))

    # Get all settings
    settings = SettingsFinance.query.all()

    # Create a simple HTML table to display settings
    html = '<html><head><title>Settings</title><style>table {border-collapse: collapse; width: 100%;} th, td {border: 1px solid #ddd; padding: 8px; text-align: left;} tr:nth-child(even) {background-color: #f2f2f2;} th {background-color: #4CAF50; color: white;}</style></head><body>'
    html += '<h1>Finance Settings</h1>'
    html += '<table>'
    html += '<tr><th>ID</th><th>Setting Name</th><th>Setting Value</th><th>Description</th><th>Parent Drive Folder</th><th>Parent Drive ID</th></tr>'

    for setting in settings:
        html += f'<tr>'
        html += f'<td>{setting.id}</td>'
        html += f'<td>{setting.setting_name}</td>'
        html += f'<td>{setting.setting_value}</td>'
        html += f'<td>{setting.description}</td>'
        html += f'<td>{setting.parent_drive_folder}</td>'
        html += f'<td>{setting.parent_drive_id}</td>'
        html += f'</tr>'

    html += '</table>'

    # Get all cost centers
    cost_centers = CostCenter.query.all()

    html += '<h1>Cost Centers with Drive IDs</h1>'
    html += '<table>'
    html += '<tr><th>ID</th><th>Cost Center</th><th>City</th><th>Drive ID</th></tr>'

    for cc in cost_centers:
        html += f'<tr>'
        html += f'<td>{cc.id}</td>'
        html += f'<td>{cc.costcenter}</td>'
        html += f'<td>{cc.city}</td>'
        html += f'<td>{cc.drive_id or "Not set"}</td>'
        html += f'</tr>'

    html += '</table>'
    html += '<p><a href="/dashboard">Back to Dashboard</a></p>'
    html += '</body></html>'

    return html

# Route to handle approval requests
@app.route('/send-for-approval', methods=['POST'])
def send_for_approval():
    # Check if user is logged in via session
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'You must be logged in to send approval requests'}), 401

    try:
        data = request.json
        epv_id = data.get('epv_id')
        approval_option = data.get('approval_option')
        emails = []

        if approval_option == 'yes':
            manager_email = data.get('manager_email')
            if manager_email:
                emails = [manager_email]
        else:
            emails = data.get('custom_emails', [])

        if not epv_id:
            return jsonify({'success': False, 'message': 'EPV ID is required'}), 400

        if not emails:
            return jsonify({'success': False, 'message': 'At least one email address is required'}), 400

        # Find the EPV record
        epv = EPV.query.filter_by(epv_id=epv_id).first()
        if not epv:
            return jsonify({'success': False, 'message': 'EPV record not found'}), 404

        # Import SMTP email utilities
        from smtp_email_utils import send_approval_email

        # Get base URL for approval links
        if request.host.startswith('127.0.0.1') or request.host.startswith('localhost'):
            base_url = f"http://{request.host}"
        else:
            base_url = f"https://{request.host}"
        print(f"DEBUG: Base URL for approval links: {base_url}")

        # Import uuid for generating tokens
        import uuid
        from models import EPVApproval

        # Send emails to all approvers
        success_count = 0
        for approver_email in emails:
            print(f"DEBUG: Processing approver email: {approver_email}")
            # Create a unique token for this approval
            token = str(uuid.uuid4())
            print(f"DEBUG: Generated token: {token}")

            # Get approver name from employee_details
            approver_name = None
            approver = EmployeeDetails.query.filter_by(email=approver_email).first()
            if approver:
                approver_name = approver.name

            # Create an EPVApproval record
            approval = EPVApproval(
                epv_id=epv.id,
                approver_email=approver_email,
                approver_name=approver_name,
                status='pending',
                token=token
            )
            db.session.add(approval)
            print(f"DEBUG: Added approval record to session")

            # Send the approval email with the token
            print(f"DEBUG: Sending approval email to {approver_email}")
            try:
                success, message_id = send_approval_email(epv, approver_email, base_url, token)
                print(f"DEBUG: Email send result: {success}, message ID: {message_id}")

                if success:
                    success_count += 1
                    # Store approver email in EPV record (legacy support)
                    if not epv.approver_emails:
                        epv.approver_emails = approver_email
                    else:
                        epv.approver_emails += f", {approver_email}"
                    print(f"DEBUG: Updated EPV record with approver email")
                else:
                    print(f"WARNING: Email sending failed but continuing with approval process. Error: {message_id}")
                    # Still count as success for the approval process even if email fails
                    success_count += 1
                    # Store approver email in EPV record (legacy support)
                    if not epv.approver_emails:
                        epv.approver_emails = approver_email
                    else:
                        epv.approver_emails += f", {approver_email}"
                    print(f"DEBUG: Updated EPV record with approver email despite email failure")
            except Exception as email_error:
                print(f"ERROR sending email to {approver_email}: {str(email_error)}")
                import traceback
                print(f"DEBUG: Email error traceback: {traceback.format_exc()}")
                # Still count as success for the approval process even if email fails completely
                success_count += 1
                # Store approver email in EPV record (legacy support)
                if not epv.approver_emails:
                    epv.approver_emails = approver_email
                else:
                    epv.approver_emails += f", {approver_email}"
                print(f"DEBUG: Updated EPV record with approver email despite email exception")

        # Update the EPV record to indicate approval has been requested
        epv.status = 'pending_approval'
        db.session.commit()
        print(f"DEBUG: Committed changes to database, updated EPV status to pending_approval")

        if success_count > 0:
            return jsonify({
                'success': True,
                'message': f"Approval request sent to {success_count} recipient(s)"
            })
        else:
            return jsonify({
                'success': False,
                'message': "Failed to send approval emails. Please try again later."
            }), 500

    except Exception as e:
        print(f"ERROR sending approval request: {str(e)}")
        import traceback
        print(f"DEBUG: Approval request error traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f"Error: {str(e)}"}), 500

# Route to approve an expense
@app.route('/approve-expense/<epv_id>')
def approve_expense(epv_id):
    try:
        # Get the token from the request
        token = request.args.get('token')

        # Find the EPV record
        epv = EPV.query.filter_by(epv_id=epv_id).first()
        if not epv:
            return render_template('error.html', error="EPV record not found"), 404

        # Find the approval record if token is provided
        approval = None
        approver_email = request.args.get('email', 'Unknown')

        if token:
            # Find the approval record by token
            from models import EPVApproval
            approval = EPVApproval.query.filter_by(epv_id=epv.id, token=token).first()

            if approval:
                # Check if the approver has already taken action
                if approval.status != 'pending':
                    return render_template('error.html',
                                          error="You have already {0} this expense.".format(approval.status),
                                          message="You cannot change your decision once submitted."), 400

                # Update the approval record
                approval.status = 'approved'
                approval.action_date = datetime.now()
                approval.comments = request.args.get('comments', '')
                approver_email = approval.approver_email
            else:
                return render_template('error.html', error="Invalid approval token"), 400

        # Update the legacy fields for backward compatibility
        epv.approved_by = approver_email
        epv.approved_on = datetime.now()

        # Check if all approvers have approved
        all_approved = True
        any_rejected = False

        # Get all approval records for this EPV
        from models import EPVApproval
        approvals = EPVApproval.query.filter_by(epv_id=epv.id).all()

        for appr in approvals:
            if appr.status == 'rejected':
                any_rejected = True
                break
            elif appr.status != 'approved':
                all_approved = False

        # Update the EPV status based on approval status
        if any_rejected:
            epv.status = 'rejected'
        elif all_approved and len(approvals) > 0:
            epv.status = 'approved'

            # If this is a sub-invoice, check if all sub-invoices of the master are approved
            if epv.invoice_type == 'sub' and epv.master_invoice_id:
                # Get the master invoice
                master_invoice = EPV.query.get(epv.master_invoice_id)
                if master_invoice:
                    # Get all sub-invoices for this master
                    sub_invoices = EPV.query.filter_by(master_invoice_id=master_invoice.id).all()

                    # Check if all sub-invoices are approved
                    all_subs_approved = True
                    for sub in sub_invoices:
                        if sub.status != 'approved':
                            all_subs_approved = False
                            break

                    # If all sub-invoices are approved, update the master invoice status
                    if all_subs_approved and len(sub_invoices) > 0:
                        master_invoice.split_status = 'fully_approved'
                        # Also update the master invoice's status to 'approved' so it shows up in finance dashboard
                        master_invoice.status = 'approved'
                        master_invoice.approved_by = approver_email
                        master_invoice.approved_on = datetime.now()
                        print(f"DEBUG: Updated master invoice {master_invoice.epv_id} status to fully_approved and approved")
        else:
            epv.status = 'partially_approved'

            # If this is a sub-invoice, update the master invoice status
            if epv.invoice_type == 'sub' and epv.master_invoice_id:
                master_invoice = EPV.query.get(epv.master_invoice_id)
                if master_invoice and master_invoice.split_status != 'partially_approved':
                    master_invoice.split_status = 'partially_approved'
                    print(f"DEBUG: Updated master invoice {master_invoice.epv_id} status to partially_approved")

        db.session.commit()

        # Render a success page
        print(f"DEBUG: Token value in approve_expense: {token}")
        return render_template('approval_result.html',
                              result="approved",
                              epv=epv,
                              token=token,
                              message="The expense has been approved successfully.")

    except Exception as e:
        print(f"Error approving expense: {str(e)}")
        return render_template('error.html', error=f"An error occurred: {str(e)}"), 500

# Route to show rejection form
@app.route('/reject-expense/<epv_id>')
def reject_expense(epv_id):
    try:
        # Get the token from the request
        token = request.args.get('token')

        # Find the EPV record
        epv = EPV.query.filter_by(epv_id=epv_id).first()
        if not epv:
            return render_template('error.html', error="EPV record not found"), 404

        # Find the approval record if token is provided
        approval = None
        approver_email = request.args.get('email', 'Unknown')

        if token:
            # Find the approval record by token
            from models import EPVApproval
            approval = EPVApproval.query.filter_by(epv_id=epv.id, token=token).first()

            if approval:
                # Check if the approver has already taken action
                if approval.status != 'pending':
                    return render_template('error.html',
                                          error="You have already {0} this expense.".format(approval.status),
                                          message="You cannot change your decision once submitted."), 400

                # Show the rejection form
                try:
                    return render_template('rejection_form.html',
                                          epv=epv,
                                          token=token,
                                          approver_email=approval.approver_email)
                except Exception as template_error:
                    print(f"Template error: {str(template_error)}")
                    # Fallback to a simpler form if there's a template error
                    return render_template('error.html',
                                          error="Please provide a reason for rejection",
                                          message=f"<form action='{url_for('process_rejection', epv_id=epv_id)}' method='POST'>"
                                                  f"<input type='hidden' name='token' value='{token}'>"
                                                  f"<input type='hidden' name='email' value='{approval.approver_email}'>"
                                                  f"<div class='mb-3'><label for='reason'>Reason:</label>"
                                                  f"<textarea name='reason' id='reason' rows='4' class='form-control' required></textarea></div>"
                                                  f"<button type='submit' class='btn btn-danger'>Reject</button></form>")
            else:
                return render_template('error.html', error="Invalid rejection token"), 400

        # If no token, show the rejection form with the provided email
        try:
            return render_template('rejection_form.html',
                                  epv=epv,
                                  token=token,
                                  approver_email=approver_email)
        except Exception as template_error:
            print(f"Template error: {str(template_error)}")
            # Fallback to a simpler form if there's a template error
            return render_template('error.html',
                                  error="Please provide a reason for rejection",
                                  message=f"<form action='{url_for('process_rejection', epv_id=epv_id)}' method='POST'>"
                                          f"<input type='hidden' name='email' value='{approver_email}'>"
                                          f"<div class='mb-3'><label for='reason'>Reason:</label>"
                                          f"<textarea name='reason' id='reason' rows='4' class='form-control' required></textarea></div>"
                                          f"<button type='submit' class='btn btn-danger'>Reject</button></form>")

    except Exception as e:
        print(f"Error showing rejection form: {str(e)}")
        return render_template('error.html', error=f"An error occurred: {str(e)}"), 500

# Route to process rejection
@app.route('/process-rejection/<epv_id>', methods=['POST'])
def process_rejection(epv_id):
    try:
        # Get form data
        token = request.form.get('token')
        approver_email = request.form.get('email', 'Unknown')
        rejection_reason = request.form.get('reason', '')

        # Validate rejection reason
        if not rejection_reason:
            return render_template('error.html',
                                  error="Rejection reason is required",
                                  message="Please provide a reason for rejecting this expense."), 400

        # Find the EPV record
        epv = EPV.query.filter_by(epv_id=epv_id).first()
        if not epv:
            return render_template('error.html', error="EPV record not found"), 404

        # Find the approval record if token is provided
        approval = None

        print(f"DEBUG: Rejection reason: {rejection_reason}")

        if token:
            # Find the approval record by token
            from models import EPVApproval
            approval = EPVApproval.query.filter_by(epv_id=epv.id, token=token).first()

            if approval:
                # Check if the approver has already taken action
                if approval.status != 'pending':
                    return render_template('error.html',
                                          error="You have already {0} this expense.".format(approval.status),
                                          message="You cannot change your decision once submitted."), 400

                # Update the approval record
                approval.status = 'rejected'
                approval.action_date = datetime.now()
                approval.comments = rejection_reason
                approver_email = approval.approver_email
            else:
                return render_template('error.html', error="Invalid rejection token"), 400

        # Update the legacy fields for backward compatibility
        epv.rejected_by = approver_email
        epv.rejected_on = datetime.now()
        epv.rejection_reason = rejection_reason

        # If any approver rejects, the entire EPV is rejected
        epv.status = 'rejected'

        # If this is a sub-invoice, update the master invoice status
        if epv.invoice_type == 'sub' and epv.master_invoice_id:
            master_invoice = EPV.query.get(epv.master_invoice_id)
            if master_invoice:
                master_invoice.split_status = 'rejected'
                print(f"DEBUG: Updated master invoice {master_invoice.epv_id} status to rejected")

        db.session.commit()

        # Send rejection notification email to the submitter using SMTP
        try:
            # Get approver name for better notification
            approver_name = approver_email
            approver = EmployeeDetails.query.filter_by(email=approver_email).first()
            if approver:
                approver_name = f"{approver.name} ({approver_email})"

            # Import SMTP email utilities
            from smtp_email_utils import send_rejection_notification_email

            # Send rejection notification email
            success, message_id = send_rejection_notification_email(
                epv_record=epv,
                rejected_by=approver_name,
                rejection_reason=rejection_reason
            )

            if success:
                print(f"DEBUG: Successfully sent rejection notification email to {epv.email_id}")
            else:
                print(f"DEBUG: Failed to send rejection notification email: {message_id}")
        except Exception as email_error:
            print(f"ERROR sending rejection notification email: {str(email_error)}")
            import traceback
            print(f"DEBUG: Email error traceback: {traceback.format_exc()}")
            # Don't fail the whole process if email sending fails
            pass

        # Render a success page
        print(f"DEBUG: Token value in reject_expense: {token}")
        return render_template('approval_result.html',
                              result="rejected",
                              epv=epv,
                              token=token,
                              message="The expense has been rejected.")

    except Exception as e:
        print(f"Error rejecting expense: {str(e)}")
        return render_template('error.html', error=f"An error occurred: {str(e)}"), 500

# API endpoint to get notification counts for the current user
@app.route('/api/notifications/count')
def get_notification_count():
    if not session.get('email'):
        return jsonify({'error': 'Not logged in'}), 401

    try:
        # Get the current user's role
        user_role = session.get('employee_role')
        user_email = session.get('email')

        # Initialize notification counts
        notifications = {
            'total': 0,
            'pending_approval': 0,
            'finance_pending': 0,
            'finance_approval': 0,
            'details': []
        }

        # Get employee details
        employee = EmployeeDetails.query.filter_by(email=user_email).first()

        if not employee:
            return jsonify(notifications)

        # For all users: Count EPVs pending approval that they submitted
        if user_role:
            # Count pending EPVs submitted by this user
            pending_submitted = EPV.query.filter_by(
                email_id=user_email,
                status='pending_approval'
            ).count()

            notifications['pending_approval'] = pending_submitted
            notifications['total'] += pending_submitted

            if pending_submitted > 0:
                notifications['details'].append({
                    'type': 'pending_approval',
                    'count': pending_submitted,
                    'message': f'You have {pending_submitted} expense(s) pending approval'
                })

        # For managers: Count EPVs waiting for their approval
        pending_approvals = EPVApproval.query.join(EPV).filter(
            EPVApproval.approver_email == user_email,
            EPVApproval.status == 'pending',
            EPV.status.in_(['pending_approval', 'partially_approved'])
        ).count()

        if pending_approvals > 0:
            notifications['pending_approval'] += pending_approvals
            notifications['total'] += pending_approvals
            notifications['details'].append({
                'type': 'manager_approval',
                'count': pending_approvals,
                'message': f'You have {pending_approvals} expense(s) to approve'
            })

        # For Finance role: Count EPVs ready for processing
        if user_role == 'Finance':
            # Get assigned cities
            assigned_cities = CityAssignment.query.filter_by(
                employee_id=employee.id,
                is_active=True
            ).all()

            city_names = [assignment.city for assignment in assigned_cities]

            if city_names:
                # Count EPVs ready for finance processing
                # Only count expenses with direct city match to assigned cities
                direct_city_count = EPV.query.filter(
                    EPV.status == 'approved',
                    EPV.city.in_(city_names),
                    db.or_(EPV.finance_status == 'pending', EPV.finance_status == None)
                ).count()

                # Then count expenses without city but with cost center city match
                cost_center_city_count = EPV.query.join(CostCenter).filter(
                    EPV.status == 'approved',
                    EPV.city == None,  # Only count expenses without a direct city
                    CostCenter.city.in_(city_names),
                    db.or_(EPV.finance_status == 'pending', EPV.finance_status == None)
                ).count()

                # Total count
                finance_pending_count = direct_city_count + cost_center_city_count

                notifications['finance_pending'] = finance_pending_count
                notifications['total'] += finance_pending_count

                if finance_pending_count > 0:
                    notifications['details'].append({
                        'type': 'finance_pending',
                        'count': finance_pending_count,
                        'message': f'You have {finance_pending_count} expense(s) to process'
                    })

        # For Finance Approver role: Count finance entries waiting for approval
        if user_role == 'Finance Approver':
            # Get assigned cities
            assigned_cities = CityAssignment.query.filter_by(
                employee_id=employee.id,
                is_active=True
            ).all()

            city_names = [assignment.city for assignment in assigned_cities]

            # Count finance entries pending approval
            if city_names:
                finance_approval_count = FinanceEntry.query.join(EPV).join(CostCenter).filter(
                    FinanceEntry.status == 'pending',
                    CostCenter.city.in_(city_names)
                ).count()
            else:
                # If no cities assigned, count all pending entries
                finance_approval_count = FinanceEntry.query.filter_by(
                    status='pending'
                ).count()

            notifications['finance_approval'] = finance_approval_count
            notifications['total'] += finance_approval_count

            if finance_approval_count > 0:
                notifications['details'].append({
                    'type': 'finance_approval',
                    'count': finance_approval_count,
                    'message': f'You have {finance_approval_count} finance entries to approve'
                })

        return jsonify(notifications)
    except Exception as e:
        print(f"Error getting notification count: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Route to view a specific EPV record
@app.route('/epv-record/<epv_id>')
def view_epv_record(epv_id):
    try:
        # Get the token from the request
        token = request.args.get('token')

        # Find the EPV record
        epv = EPV.query.filter_by(epv_id=epv_id).first()
        if not epv:
            return render_template('error.html', error="EPV record not found"), 404

        # Get EPV items
        epv_items = EPVItem.query.filter_by(epv_id=epv.id).all()

        # Get approval records
        from models import EPVApproval
        approvals = EPVApproval.query.filter_by(epv_id=epv.id).all()

        # Check if the user is an approver with a valid token
        is_approver = False
        current_approval = None

        if token:
            current_approval = EPVApproval.query.filter_by(epv_id=epv.id, token=token).first()
            if current_approval:
                is_approver = True

        # Render the EPV record view
        return render_template('epv_record_view.html',
                              epv=epv,
                              epv_items=epv_items,
                              approvals=approvals,
                              is_approver=is_approver,
                              current_approval=current_approval,
                              token=token)

    except Exception as e:
        print(f"Error viewing EPV record: {str(e)}")
        return render_template('error.html', error=f"An error occurred: {str(e)}"), 500

# Route to view all EPV records
@app.route('/epv-records')
def epv_records():
    # Check if user is logged in
    if 'email' not in session:
        print("DEBUG: User not logged in, redirecting to login")
        return redirect(url_for('login', next='/epv-records'))

    print(f"DEBUG: EPV Records accessed by {session.get('email')}")
    print(f"DEBUG: Session data: {session}")

    # Get the user's role
    user_email = session.get('email')
    employee = EmployeeDetails.query.filter_by(email=user_email).first()
    role = employee.role if employee else 'user'

    # Get filter options
    expense_heads = ExpenseHead.query.filter_by(is_active=True).all()
    cost_centers = CostCenter.query.filter_by(is_active=True).all()

    # Get filter values from request
    expense_head_filter = request.args.get('expense_head', '')
    cost_center_filter = request.args.get('cost_center', '')
    status_filter = request.args.get('status', '')
    time_period_filter = request.args.get('time_period', 'all')
    view_mode = request.args.get('view', '')
    city_filter = request.args.get('city', '')

    # Get cities for the filter dropdown (for finance users)
    cities = []
    if role in ['Finance', 'Finance Approver', 'Super Admin']:
        # For Finance users, show only assigned cities
        if role == 'Finance':
            # Get the employee ID from the email
            employee = EmployeeDetails.query.filter_by(email=user_email).first()
            if employee:
                # Get the city assignments for this employee
                city_assignments = CityAssignment.query.filter_by(employee_id=employee.id, is_active=True).all()
                cities = [ca.city for ca in city_assignments if ca.city]
        # For Finance Approver and Super Admin, show all cities
        else:
            # Get all unique cities from cost centers
            cities = db.session.query(CostCenter.city).distinct().filter(CostCenter.city.isnot(None)).all()
            cities = [city[0] for city in cities if city[0]]  # Extract city names and filter out None values

    # Define time period filter dates
    today = datetime.now().date()
    if time_period_filter == 'this_month':
        start_date = datetime(today.year, today.month, 1).date()
        end_date = today
    elif time_period_filter == 'last_month':
        if today.month == 1:
            start_date = datetime(today.year - 1, 12, 1).date()
            end_date = datetime(today.year, 1, 1).date() - timedelta(days=1)
        else:
            start_date = datetime(today.year, today.month - 1, 1).date()
            end_date = datetime(today.year, today.month, 1).date() - timedelta(days=1)
    elif time_period_filter == 'this_year':
        start_date = datetime(today.year, 1, 1).date()
        end_date = today
    else:  # 'all'
        start_date = None
        end_date = None

    # Base query for EPV records
    if role == 'Super Admin':
        # Super admins can see all records
        base_query = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices))
    elif role in ['Finance', 'Finance Approver'] and view_mode != 'my_expenses':
        # Finance users see records based on their assigned cities
        if role == 'Finance':
            # Get the employee ID from the email
            employee = EmployeeDetails.query.filter_by(email=user_email).first()
            if employee:
                # Get the city assignments for this employee
                city_assignments = CityAssignment.query.filter_by(employee_id=employee.id, is_active=True).all()
                assigned_cities = [ca.city for ca in city_assignments if ca.city]

                if assigned_cities:
                    # Get cost centers in the assigned cities
                    assigned_cost_center_ids = db.session.query(CostCenter.id).filter(CostCenter.city.in_(assigned_cities)).all()
                    assigned_cost_center_ids = [cc_id[0] for cc_id in assigned_cost_center_ids]

                    # Base query for EPVs in assigned cost centers
                    base_query = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices)).filter(EPV.cost_center_id.in_(assigned_cost_center_ids))

                    # If city filter is applied, filter by that specific city
                    if city_filter and city_filter in assigned_cities:
                        city_cost_center_ids = db.session.query(CostCenter.id).filter(CostCenter.city == city_filter).all()
                        city_cost_center_ids = [cc_id[0] for cc_id in city_cost_center_ids]

                        if city_cost_center_ids:
                            base_query = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices)).filter(EPV.cost_center_id.in_(city_cost_center_ids))
                else:
                    # If no cities assigned, show no EPVs
                    base_query = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices)).filter(EPV.id == -1)  # This will return no results
            else:
                # If employee not found, show no EPVs
                base_query = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices)).filter(EPV.id == -1)  # This will return no results
        else:
            # Finance Approver can see all records by default
            base_query = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices))

            # Apply city filter if provided
            if city_filter:
                # Get cost centers in the selected city
                city_cost_center_ids = db.session.query(CostCenter.id).filter(CostCenter.city == city_filter).all()
                city_cost_center_ids = [cc_id[0] for cc_id in city_cost_center_ids]

                # Filter EPVs by cost centers in the selected city
                if city_cost_center_ids:
                    base_query = base_query.filter(EPV.cost_center_id.in_(city_cost_center_ids))
    else:
        # Regular users, admins, and finance users in 'my_expenses' view can only see their own records
        base_query = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices)).filter_by(email_id=user_email)

    # Apply filters
    if expense_head_filter:
        # Join with EPVItem to filter by expense_head
        base_query = base_query.join(EPVItem, EPV.id == EPVItem.epv_id)
        base_query = base_query.filter(EPVItem.expense_head == expense_head_filter)
        # Make sure we get distinct EPVs (to avoid duplicates from the join)
        base_query = base_query.distinct()

    if cost_center_filter:
        base_query = base_query.filter(EPV.cost_center_name == cost_center_filter)

    if status_filter:
        # Handle status filter with exact match (case sensitive)
        base_query = base_query.filter(EPV.status == status_filter)

    if start_date and end_date:
        # Filter by submission date
        base_query = base_query.filter(EPV.submission_date.between(start_date, end_date))

    # Debug the SQL query
    print(f"DEBUG: SQL Query: {str(base_query)}")

    # Get the filtered records
    records = base_query.order_by(EPV.submission_date.desc()).all()

    # Debug output
    for record in records:
        print(f"DEBUG: EPV ID: {record.epv_id}, Employee: {record.employee_name}, Email: {record.email_id}, Status: {record.status}, Type: {record.invoice_type}")

    # Calculate scorecard data
    total_records = len(records)
    pending_count = sum(1 for record in records if record.status in ['submitted', 'pending_approval'])
    approved_count = sum(1 for record in records if record.status == 'approved')
    rejected_count = sum(1 for record in records if record.status == 'rejected')

    # Calculate total amount
    total_amount = sum(record.total_amount for record in records if record.total_amount)
    formatted_total_amount = f"Rs. {total_amount:,.2f}"

    # Prepare scorecard data
    scorecard_data = {
        'total_records': total_records,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_amount': formatted_total_amount
    }

    # Debug output
    print(f"DEBUG: User role: {role}")
    print(f"DEBUG: Found {len(records)} EPV records")
    for record in records:
        print(f"DEBUG: EPV ID: {record.epv_id}, Employee: {record.employee_name}, Email: {record.email_id}, Status: {record.status}")

    # Return the EPV records template
    print("DEBUG: Rendering epv_records.html template")
    try:
        return render_template('epv_records_new.html',
                           records=records,
                           cost_centers=cost_centers,
                           expense_heads=expense_heads,
                           cities=cities,
                           scorecard_data=scorecard_data,
                           selected_expense_head=expense_head_filter,
                           selected_cost_center=cost_center_filter,
                           selected_status=status_filter,
                           selected_time_period=time_period_filter,
                           selected_city=city_filter,
                           view_mode=view_mode,
                           is_finance_user=(role in ['Finance', 'Finance Approver']),
                           user=session.get('user_info'))
    except Exception as e:
        print(f"DEBUG: Error rendering template: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return f"Error: {str(e)}", 500

# Route to view a specific EPV record
@app.route('/epv-record/<epv_id>')
def epv_record(epv_id):
    # Check if user is logged in
    if 'email' not in session:
        return redirect(url_for('login'))

    # Get the user's role
    user_email = session.get('email')
    employee = EmployeeDetails.query.filter_by(email=user_email).first()
    role = employee.role if employee else 'user'

    # Get the EPV record with finance entry and sub-invoices relationships
    record = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices)).filter_by(epv_id=epv_id).first_or_404()

    # Fix cost center display if it's an object
    if hasattr(record, 'cost_center') and record.cost_center and str(record.cost_center).startswith('<CostCenter'):
        # Extract just the name from the CostCenter object
        cost_center_name = str(record.cost_center).split(' ')[1].rstrip('>')
        record.cost_center = cost_center_name

    # Check if the user has permission to view this record
    if role != 'Super Admin' and record.email_id != user_email:
        print(f"DEBUG: Access denied for user {user_email} to view EPV {epv_id}")
        return redirect(url_for('epv_records'))

    # Get the expense items for this EPV
    items = EPVItem.query.filter_by(epv_id=record.id).all()

    # Get approval information
    approvals = EPVApproval.query.filter_by(epv_id=record.id).all()

    # Check if the current user is an approver for this EPV
    is_approver = False
    already_approved = False
    token = request.args.get('token', '')

    if token:
        approval = EPVApproval.query.filter_by(token=token).first()
        if approval and approval.epv_id == record.id:
            is_approver = True
            already_approved = approval.status in ['Approved', 'Rejected']

    # Get employee names for approvers and processors
    manager_name = None
    rejector_name = None

    # Get manager name if approved
    if record.approved_by:
        approver = EmployeeDetails.query.filter_by(email=record.approved_by).first()
        if approver and approver.name:
            # Use the approver's name field
            manager_name = approver.name
        else:
            # Fallback to email if name is not found
            manager_name = record.approved_by

    # Get rejector name if rejected
    if record.rejected_by:
        rejector = EmployeeDetails.query.filter_by(email=record.rejected_by).first()
        if rejector and rejector.name:
            # Use the rejector's name field
            rejector_name = rejector.name
        else:
            # Fallback to email if name is not found
            rejector_name = record.rejected_by

    # Get all employee details for template
    employee_details = EmployeeDetails.query.all()

    print(f"DEBUG: User {user_email} viewing EPV record {epv_id}")
    return render_template('epv_record_view.html',
                           epv=record,
                           expense_items=items,
                           approvals=approvals,
                           is_approver=is_approver,
                           already_approved=already_approved,
                           token=token,
                           user=session.get('user_info'),
                           manager_name=manager_name,
                           rejector_name=rejector_name,
                           employee_details=employee_details)

# Cost Center Admin View
@app.route('/cost-center-admin')
@login_required
def cost_center_admin():
    """View for cost center administrators to see all EPVs related to their cost centers"""
    # Check if user is logged in
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session.get('email')

    # Check if the user is a cost center admin (approver)
    cost_centers = CostCenter.query.filter_by(approver_email=user_email, is_active=True).all()

    if not cost_centers:
        flash('You do not have permission to access this page. You are not assigned as an approver for any cost center.', 'error')
        return redirect(url_for('dashboard'))

    # Get filter options
    expense_heads = ExpenseHead.query.filter_by(is_active=True).all()

    # Add debug logging
    print(f"DEBUG: Cost Center Admin accessed by {user_email}")
    print(f"DEBUG: Found {len(cost_centers)} cost centers for this approver")

    # Get filter values from request
    expense_head_filter = request.args.get('expense_head', '')
    cost_center_filter = request.args.get('cost_center', '')
    status_filter = request.args.get('status', '')
    time_period_filter = request.args.get('time_period', 'all')

    # Define time period filter dates
    today = datetime.now().date()
    if time_period_filter == 'this_month':
        start_date = datetime(today.year, today.month, 1).date()
        end_date = today
    elif time_period_filter == 'last_month':
        if today.month == 1:
            start_date = datetime(today.year - 1, 12, 1).date()
            end_date = datetime(today.year, 1, 1).date() - timedelta(days=1)
        else:
            start_date = datetime(today.year, today.month - 1, 1).date()
            end_date = datetime(today.year, today.month, 1).date() - timedelta(days=1)
    elif time_period_filter == 'this_year':
        start_date = datetime(today.year, 1, 1).date()
        end_date = today
    else:  # 'all'
        start_date = None
        end_date = None

    # Get the cost center IDs that the user administers
    cost_center_ids = [cc.id for cc in cost_centers]

    # Base query for EPV records - filter by the cost centers the user administers
    base_query = EPV.query.options(db.joinedload(EPV.finance_entry)).options(db.joinedload(EPV.sub_invoices)).filter(EPV.cost_center_id.in_(cost_center_ids))

    # Apply additional filters
    if expense_head_filter:
        # Join with EPVItem to filter by expense_head
        base_query = base_query.join(EPVItem, EPV.id == EPVItem.epv_id)
        base_query = base_query.filter(EPVItem.expense_head == expense_head_filter)

    if cost_center_filter:
        base_query = base_query.filter(EPV.cost_center_name == cost_center_filter)

    if status_filter:
        base_query = base_query.filter(EPV.status == status_filter)

    if start_date and end_date:
        base_query = base_query.filter(EPV.submission_date.between(start_date, end_date))

    # Get the filtered records
    records = base_query.order_by(EPV.submission_date.desc()).all()

    # Calculate scorecard data
    total_records = len(records)
    pending_count = sum(1 for record in records if record.status in ['submitted', 'pending_approval'])
    approved_count = sum(1 for record in records if record.status == 'approved')
    rejected_count = sum(1 for record in records if record.status == 'rejected')

    # Calculate total amount
    total_amount = sum(record.total_amount for record in records if record.total_amount)
    formatted_total_amount = f"Rs. {total_amount:,.2f}"

    # Prepare scorecard data
    scorecard_data = {
        'total_records': total_records,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_amount': formatted_total_amount
    }

    # Return the cost center admin template
    return render_template('cost_center_admin.html',
                          records=records,
                          cost_centers=cost_centers,
                          expense_heads=expense_heads,
                          scorecard_data=scorecard_data,
                          selected_expense_head=expense_head_filter,
                          selected_cost_center=cost_center_filter,
                          selected_status=status_filter,
                          selected_time_period=time_period_filter,
                          user=session.get('user_info'))



# Add a before_request handler to check token expiration
@app.before_request
def check_token_expiration():
    """Check if the token is expired before each request"""
    # Skip for static files and certain routes
    if request.path.startswith('/static') or request.path in ['/', '/login', '/logout', '/refresh-token']:
        return

    # Skip if not authenticated
    if not current_user.is_authenticated:
        return

    # Skip if no Google token
    if not google.authorized:
        return

    # Check if token is valid
    try:
        # Make a simple API call to check token validity
        resp = google.get('/oauth2/v2/userinfo')
        if not resp.ok:
            # If token refresh failed, redirect to refresh token page
            flash("Your Google token has expired. Please refresh it.")
            return redirect(url_for('refresh_token', next=request.path))
    except Exception as e:
        print(f"ERROR: Token validation failed in before_request: {str(e)}")
        # If there's an exception, redirect to refresh token page
        flash("Your Google token has expired. Please refresh it.")
        return redirect(url_for('refresh_token', next=request.path))

# Reject EPV by Finance Personnel
@app.route('/reject-finance-epv/<epv_id>', methods=['POST'])
@login_required
def reject_finance_epv(epv_id):
    # Check if user has finance role
    if session.get('employee_role') != 'Finance':
        flash('You do not have permission to reject this EPV.', 'danger')
        return redirect(url_for('finance_dashboard'))

    # Get the EPV record
    epv = EPV.query.filter_by(epv_id=epv_id).first_or_404()

    # Get the rejection reason and type
    rejection_reason = request.form.get('rejection_reason')
    rejection_type = request.form.get('rejection_type')

    if not rejection_reason:
        flash('Rejection reason is required.', 'danger')
        return redirect(url_for('finance_entry', epv_id=epv_id))

    if not rejection_type:
        flash('Rejection type is required.', 'danger')
        return redirect(url_for('finance_entry', epv_id=epv_id))

    # Get finance user details
    finance_user_email = session.get('email')
    finance_user = EmployeeDetails.query.filter_by(email=finance_user_email).first()
    finance_user_name = finance_user.name if finance_user else finance_user_email

    # Format the rejection reason with finance user details
    formatted_rejection_reason = f"[FINANCE REJECTION] {rejection_reason}\n\nRejected by: {finance_user_email}\nRejected on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Handle based on rejection type
    if rejection_type == 'upload_missing':
        # Set status for supplementary document upload
        epv.status = 'rejected'
        epv.finance_status = 'pending_documents'
        epv.document_status = 'pending_additional_documents'
        epv.requested_documents = rejection_reason

        # Add a note to the rejection reason
        formatted_rejection_reason += "\n\nAction Required: Upload missing documents"
    else:  # restart_process
        # Full rejection - no supplementary document process
        epv.status = 'rejected'
        epv.finance_status = 'rejected'  # This is critical for showing the rejected status
        epv.document_status = 'complete'  # Reset document status

        # Add a note to the rejection reason
        formatted_rejection_reason += "\n\nAction Required: Create a new EPV"

    # Store rejection reason in the existing rejection_reason field
    epv.rejection_reason = formatted_rejection_reason

    # Release the claim on this EPV
    epv.being_processed_by = None
    epv.processing_started_at = None

    # Save the changes
    db.session.commit()

    # Print debug information
    print(f"EPV rejected with type '{rejection_type}': status={epv.status}, finance_status={epv.finance_status}, document_status={epv.document_status}")

    # Send rejection notification email to the submitter using SMTP
    try:
        # Format the finance user name for the email
        rejected_by = f"{finance_user_name} (Finance Team)"

        # Import SMTP email utilities
        from smtp_email_utils import send_rejection_notification_email

        # Send rejection notification email
        success, message_id = send_rejection_notification_email(
            epv_record=epv,
            rejected_by=rejected_by,
            rejection_reason=rejection_reason
        )

        if success:
            print(f"DEBUG: Successfully sent finance rejection notification email to {epv.email_id}")
        else:
            print(f"DEBUG: Failed to send finance rejection notification email: {message_id}")
    except Exception as email_error:
        print(f"ERROR sending finance rejection notification email: {str(email_error)}")
        import traceback
        print(f"DEBUG: Email error traceback: {traceback.format_exc()}")
        # Don't fail the whole process if email sending fails
        pass

    flash('EPV has been rejected.', 'success')
    return redirect(url_for('finance_dashboard'))

# Finance Dashboard
@app.route('/finance-dashboard')
@login_required
def finance_dashboard():
    # Check if user has Finance role
    if session.get('employee_role') not in ['Finance', 'Finance Approver']:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))

    # Get the employee's database ID from their email
    employee = EmployeeDetails.query.filter_by(email=session.get('email')).first()

    if not employee:
        flash('Error: Could not find your user account.', 'error')
        return redirect(url_for('dashboard'))

    # Debug logging for filters
    print(f"DEBUG: Finance Dashboard accessed by {session.get('email')}")
    print(f"DEBUG: Employee role: {session.get('employee_role')}")

    # Get assigned cities for the employee
    assigned_cities = CityAssignment.query.filter_by(
        employee_id=employee.id,
        is_active=True
    ).all()

    city_names = [assignment.city for assignment in assigned_cities]

    if session.get('employee_role') == 'Finance':
        # For Finance Personnel

        # Get pending EPVs (approved but not processed)
        pending_epvs = []
        resubmitted_epvs = []
        rejected_epvs = []
        pending_payment_epvs = []

        # Get ALL standard invoices that are approved and have pending/null finance status
        standard_invoices_query = EPV.query.filter(
            EPV.invoice_type == 'standard',
            EPV.status == 'approved',
            (EPV.finance_status == None) | (EPV.finance_status == 'pending'),
            EPV.document_status != 'documents_uploaded'  # Exclude resubmitted documents
        )

        standard_invoices = standard_invoices_query.all()

        # Get resubmitted EPVs (documents uploaded after rejection)
        resubmitted_invoices_query = EPV.query.filter(
            EPV.invoice_type == 'standard',
            EPV.status == 'approved',
            EPV.finance_status == 'pending',
            EPV.document_status == 'documents_uploaded'  # These are resubmitted documents
        )

        resubmitted_invoices = resubmitted_invoices_query.all()

        # Get rejected EPVs
        rejected_invoices_query = EPV.query.filter(
            EPV.invoice_type == 'standard',
            EPV.finance_status == 'rejected'
        )

        rejected_invoices = rejected_invoices_query.all()

        # Get EPVs that need payment details (approved by Finance Approver but missing transaction ID or payment date)
        # This query finds finance entries that are approved but have null transaction_id or payment_date
        pending_payment_query = db.session.query(EPV).join(FinanceEntry).filter(
            FinanceEntry.status == 'approved',
            db.or_(
                FinanceEntry.transaction_id == None,
                FinanceEntry.payment_date == None
            ),
            FinanceEntry.finance_user_id == employee.id  # Only show entries processed by this finance user
        )

        pending_payment_invoices = pending_payment_query.all()

        # Filter standard invoices by city if the user has assigned cities
        standard_epvs = []
        resubmitted_epvs_filtered = []
        rejected_epvs_filtered = []
        pending_payment_epvs_filtered = []

        if city_names:
            for invoice in standard_invoices:
                # If the EPV has a city field, only show it if the finance person is assigned to that exact city
                if invoice.city:
                    if invoice.city in city_names:
                        standard_epvs.append(invoice)
                # If EPV doesn't have a city, fall back to the cost center's city
                elif invoice.cost_center and invoice.cost_center.city in city_names:
                    standard_epvs.append(invoice)
                # Also include invoices that don't have a city or cost center
                elif not invoice.city and not invoice.cost_center:
                    standard_epvs.append(invoice)

            # Filter resubmitted invoices by city
            for invoice in resubmitted_invoices:
                # If the EPV has a city field, only show it if the finance person is assigned to that exact city
                if invoice.city:
                    if invoice.city in city_names:
                        resubmitted_epvs_filtered.append(invoice)
                # If EPV doesn't have a city, fall back to the cost center's city
                elif invoice.cost_center and invoice.cost_center.city in city_names:
                    resubmitted_epvs_filtered.append(invoice)
                # Also include invoices that don't have a city or cost center
                elif not invoice.city and not invoice.cost_center:
                    resubmitted_epvs_filtered.append(invoice)

            # Filter rejected invoices by city
            for invoice in rejected_invoices:
                # If the EPV has a city field, only show it if the finance person is assigned to that exact city
                if invoice.city:
                    if invoice.city in city_names:
                        rejected_epvs_filtered.append(invoice)
                # If EPV doesn't have a city, fall back to the cost center's city
                elif invoice.cost_center and invoice.cost_center.city in city_names:
                    rejected_epvs_filtered.append(invoice)
                # Also include invoices that don't have a city or cost center
                elif not invoice.city and not invoice.cost_center:
                    rejected_epvs_filtered.append(invoice)

            # Filter pending payment invoices by city
            for invoice in pending_payment_invoices:
                # If the EPV has a city field, only show it if the finance person is assigned to that exact city
                if invoice.city:
                    if invoice.city in city_names:
                        pending_payment_epvs_filtered.append(invoice)
                # If EPV doesn't have a city, fall back to the cost center's city
                elif invoice.cost_center and invoice.cost_center.city in city_names:
                    pending_payment_epvs_filtered.append(invoice)
                # Also include invoices that don't have a city or cost center
                elif not invoice.city and not invoice.cost_center:
                    pending_payment_epvs_filtered.append(invoice)
        else:
            # If the user has no assigned cities, show all invoices
            standard_epvs = standard_invoices
            resubmitted_epvs_filtered = resubmitted_invoices
            rejected_epvs_filtered = rejected_invoices
            pending_payment_epvs_filtered = pending_payment_invoices

        # Get ALL master invoices that are approved and have pending/null finance status
        # For master invoices, we don't filter by city - show all of them
        master_invoices_query = EPV.query.filter(
            EPV.invoice_type == 'master',
            EPV.status == 'approved',
            (EPV.finance_status == None) | (EPV.finance_status == 'pending')
        )

        master_epvs = master_invoices_query.all()

        # Combine the results - include both standard and master invoices
        pending_epvs = standard_epvs + master_epvs
        resubmitted_epvs = resubmitted_epvs_filtered
        rejected_epvs = rejected_epvs_filtered
        pending_payment_epvs = pending_payment_epvs_filtered

        # Check for EPVs being processed by others
        # Get the current time
        current_time = datetime.now()

        # Define a timeout period (e.g., 30 minutes)
        timeout_period = 30  # minutes

        for epv in pending_epvs:
            # Check if this EPV is being processed by someone
            if epv.being_processed_by and epv.processing_started_at:
                # Calculate how long it's been since processing started
                time_diff = current_time - epv.processing_started_at
                minutes_diff = time_diff.total_seconds() / 60

                # If it's been less than the timeout period and it's not this user
                if minutes_diff < timeout_period and epv.being_processed_by != employee.id:
                    # Mark this EPV as being processed by someone else
                    epv.is_locked = True
                    epv.locked_by = EmployeeDetails.query.get(epv.being_processed_by)
                    epv.lock_time_remaining = int(timeout_period - minutes_diff)
                else:
                    # If it's been longer than the timeout or it's this user, clear the lock
                    epv.is_locked = False
                    epv.locked_by = None
                    epv.lock_time_remaining = 0

                    # If it's been longer than the timeout, clear the processing fields
                    if minutes_diff >= timeout_period:
                        epv.being_processed_by = None
                        epv.processing_started_at = None
                        db.session.commit()
            else:
                # Not being processed
                epv.is_locked = False
                epv.locked_by = None
                epv.lock_time_remaining = 0

            # No need to check city here as we're using city_names from assignments

        # Get processed entries for the assigned cities
        if city_names:
            processed_entries = FinanceEntry.query.join(EPV).join(
                CostCenter, EPV.cost_center_id == CostCenter.id
            ).filter(
                CostCenter.city.in_(city_names)
            ).order_by(FinanceEntry.entry_date.desc()).all()
            print(f"DEBUG: Found {len(processed_entries)} processed entries for assigned cities")
        else:
            # If no cities assigned, show only entries processed by this user
            processed_entries = FinanceEntry.query.filter_by(
                finance_user_id=employee.id
            ).order_by(FinanceEntry.entry_date.desc()).all()
            print(f"DEBUG: Found {len(processed_entries)} processed entries by this finance user")

        return render_template(
            'finance_dashboard.html',
            user=session.get('user_info'),
            pending_epvs=pending_epvs,
            resubmitted_epvs=resubmitted_epvs,
            rejected_epvs=rejected_epvs,
            pending_payment_epvs=pending_payment_epvs,
            processed_entries=processed_entries,
            today=datetime.now()
        )
    else:
        # For Finance Approver

        # Get entries pending approval
        pending_approval_entries = []
        if city_names:
            # If finance approver has assigned cities, only show entries from those cities
            pending_approval_entries = FinanceEntry.query.join(EPV).join(CostCenter).filter(
                FinanceEntry.status == 'pending',
                CostCenter.city.in_(city_names)
            ).order_by(FinanceEntry.entry_date.desc()).all()
            print(f"DEBUG: Found {len(pending_approval_entries)} pending approval entries for assigned cities")
        else:
            # If no cities assigned, show all pending entries
            pending_approval_entries = FinanceEntry.query.filter_by(
                status='pending'
            ).order_by(FinanceEntry.entry_date.desc()).all()
            print(f"DEBUG: Found {len(pending_approval_entries)} pending approval entries across all cities")

        # Get approved/rejected entries by this finance approver
        approved_rejected_entries = FinanceEntry.query.filter(
            FinanceEntry.approver_id == employee.id,
            FinanceEntry.status.in_(['approved', 'rejected'])
        ).order_by(FinanceEntry.approved_on.desc()).all()
        print(f"DEBUG: Found {len(approved_rejected_entries)} approved/rejected entries by this finance approver")

        return render_template(
            'finance_dashboard.html',
            user=session.get('user_info'),
            pending_approval_entries=pending_approval_entries,
            approved_rejected_entries=approved_rejected_entries,
            today=datetime.now()
        )

# API endpoint to check for updates in the finance dashboard
@app.route('/finance-dashboard-content')
@login_required
def finance_dashboard_content():
    # Get the tab ID and current row count from the request
    tab_id = request.args.get('tab')
    current_rows_str = request.args.get('current_rows', '0')
    last_update_time_str = request.args.get('last_update', '0')

    if not tab_id:
        return jsonify({'has_updates': False})

    try:
        current_rows = int(current_rows_str)
        last_update_time = float(last_update_time_str) if last_update_time_str else 0
    except ValueError:
        current_rows = 0
        last_update_time = 0

    # Convert timestamp to datetime
    if last_update_time > 0:
        last_update_datetime = datetime.fromtimestamp(last_update_time / 1000.0)  # Convert from JS milliseconds
    else:
        last_update_datetime = datetime.now() - timedelta(minutes=30)  # Default to 30 minutes ago

    # Get the employee's database ID from their email
    employee = EmployeeDetails.query.filter_by(email=session.get('email')).first()
    if not employee:
        return jsonify({'has_updates': False})

    # Check for updates based on the tab ID
    has_updates = False

    try:
        if session.get('employee_role') == 'Finance':
            if tab_id == 'pending':
                # Check for new approved EPVs
                assigned_cities = CityAssignment.query.filter_by(
                    employee_id=employee.id,
                    is_active=True
                ).all()
                city_names = [assignment.city for assignment in assigned_cities]

                if city_names:
                    # Count the current number of pending EPVs
                    # Only count expenses with direct city match to assigned cities
                    direct_city_count = EPV.query.filter(
                        EPV.status == 'approved',
                        EPV.city.in_(city_names),
                        db.or_(EPV.finance_status == 'pending', EPV.finance_status == None)
                    ).count()

                    # Then count expenses without city but with cost center city match
                    cost_center_city_count = EPV.query.join(CostCenter).filter(
                        EPV.status == 'approved',
                        EPV.city == None,  # Only count expenses without a direct city
                        CostCenter.city.in_(city_names),
                        db.or_(EPV.finance_status == 'pending', EPV.finance_status == None)
                    ).count()

                    # Total count
                    current_count = direct_city_count + cost_center_city_count

                    # Check if the count is different
                    if current_count != current_rows:
                        has_updates = True
                    else:
                        # Check if any EPV's processing status has changed
                        recent_updates = EPV.query.outerjoin(CostCenter).filter(
                            EPV.status == 'approved',
                            db.or_(
                                EPV.city.in_(city_names),
                                CostCenter.city.in_(city_names)
                            ),
                            (EPV.finance_status == None) | (EPV.finance_status == 'pending'),
                            db.or_(
                                EPV.being_processed_by != None,  # Someone started processing
                                EPV.processing_started_at > last_update_datetime  # Processing started recently
                            )
                        ).count()

                        has_updates = recent_updates > 0

            elif tab_id == 'resubmitted':
                # Check for new resubmitted EPVs
                if city_names:
                    # Count the current number of resubmitted EPVs
                    current_count = EPV.query.outerjoin(CostCenter).filter(
                        EPV.status == 'approved',
                        db.or_(
                            EPV.city.in_(city_names),
                            CostCenter.city.in_(city_names)
                        ),
                        EPV.finance_status == 'pending',
                        EPV.document_status == 'documents_uploaded'
                    ).count()
                else:
                    # If no cities assigned, count all resubmitted EPVs
                    current_count = EPV.query.filter(
                        EPV.status == 'approved',
                        EPV.finance_status == 'pending',
                        EPV.document_status == 'documents_uploaded'
                    ).count()

                # Check if the count is different
                if current_count != current_rows:
                    has_updates = True

            elif tab_id == 'pending-payment':
                # Check for EPVs that need payment details
                # This query finds finance entries that are approved but have null transaction_id or payment_date
                pending_payment_query = db.session.query(EPV).join(FinanceEntry).filter(
                    FinanceEntry.status == 'approved',
                    db.or_(
                        FinanceEntry.transaction_id == None,
                        FinanceEntry.payment_date == None
                    ),
                    FinanceEntry.finance_user_id == employee.id  # Only show entries processed by this finance user
                )

                if city_names:
                    # Filter by city if assigned
                    # We need to handle this differently since we're already in a query
                    # First get the IDs of EPVs with direct city match
                    direct_city_epv_ids = db.session.query(EPV.id).filter(
                        EPV.city.in_(city_names)
                    ).all()
                    direct_city_epv_ids = [id[0] for id in direct_city_epv_ids]

                    # Then get the IDs of EPVs with cost center city match but no direct city
                    cost_center_city_epv_ids = db.session.query(EPV.id).join(CostCenter).filter(
                        EPV.city == None,
                        CostCenter.city.in_(city_names)
                    ).all()
                    cost_center_city_epv_ids = [id[0] for id in cost_center_city_epv_ids]

                    # Combine the IDs
                    all_epv_ids = direct_city_epv_ids + cost_center_city_epv_ids

                    # Filter the query by these IDs
                    pending_payment_query = pending_payment_query.filter(
                        EPV.id.in_(all_epv_ids)
                    )

                # Count the current number of pending payment EPVs
                current_count = pending_payment_query.count()

                # Check if the count is different
                if current_count != current_rows:
                    has_updates = True

            elif tab_id == 'rejected':
                # Check for new rejected EPVs
                if city_names:
                    # Count the current number of rejected EPVs
                    current_count = EPV.query.outerjoin(CostCenter).filter(
                        db.or_(
                            EPV.city.in_(city_names),
                            CostCenter.city.in_(city_names)
                        ),
                        EPV.finance_status == 'rejected'
                    ).count()
                else:
                    # If no cities assigned, count all rejected EPVs
                    current_count = EPV.query.filter(
                        EPV.finance_status == 'rejected'
                    ).count()

                # Check if the count is different
                if current_count != current_rows:
                    has_updates = True

            elif tab_id == 'processed':
                # Count the current number of processed entries
                current_count = FinanceEntry.query.filter(
                    FinanceEntry.finance_user_id == employee.id
                ).count()

                # Check if the count is different
                if current_count != current_rows:
                    has_updates = True
                else:
                    # Check if any entries have been updated recently
                    recent_updates = FinanceEntry.query.filter(
                        FinanceEntry.finance_user_id == employee.id,
                        FinanceEntry.entry_date > last_update_datetime
                    ).count()

                    has_updates = recent_updates > 0

        else:  # Finance Approver
            if tab_id == 'pending-approval':
                # Check for new entries pending approval
                assigned_cities = CityAssignment.query.filter_by(
                    employee_id=employee.id,
                    is_active=True
                ).all()
                city_names = [assignment.city for assignment in assigned_cities]

                if city_names:
                    # Count the current number of pending entries
                    current_count = FinanceEntry.query.join(EPV).outerjoin(CostCenter).filter(
                        FinanceEntry.status == 'pending',
                        db.or_(
                            EPV.city.in_(city_names),
                            CostCenter.city.in_(city_names)
                        )
                    ).count()

                    # Check if the count is different
                    if current_count != current_rows:
                        has_updates = True
                    else:
                        # Check if any entries have been updated recently
                        recent_updates = FinanceEntry.query.join(EPV).outerjoin(CostCenter).filter(
                            FinanceEntry.status == 'pending',
                            db.or_(
                                EPV.city.in_(city_names),
                                CostCenter.city.in_(city_names)
                            ),
                            FinanceEntry.entry_date > last_update_datetime
                        ).count()

                        has_updates = recent_updates > 0
                else:
                    # If no cities assigned, check all pending entries
                    current_count = FinanceEntry.query.filter(
                        FinanceEntry.status == 'pending'
                    ).count()

                    # Check if the count is different
                    if current_count != current_rows:
                        has_updates = True
                    else:
                        # Check if any entries have been updated recently
                        recent_updates = FinanceEntry.query.filter(
                            FinanceEntry.status == 'pending',
                            FinanceEntry.entry_date > last_update_datetime
                        ).count()

                        has_updates = recent_updates > 0

            elif tab_id == 'approved-rejected':
                # Count the current number of approved/rejected entries
                current_count = FinanceEntry.query.filter(
                    FinanceEntry.approver_id == employee.id,
                    FinanceEntry.status.in_(['approved', 'rejected'])
                ).count()

                # Check if the count is different
                if current_count != current_rows:
                    has_updates = True
                else:
                    # Check if any entries have been updated recently
                    recent_updates = FinanceEntry.query.filter(
                        FinanceEntry.approver_id == employee.id,
                        FinanceEntry.status.in_(['approved', 'rejected']),
                        db.or_(
                            FinanceEntry.approved_on > last_update_datetime,
                            FinanceEntry.entry_date > last_update_datetime
                        )
                    ).count()

                    has_updates = recent_updates > 0
    except Exception as e:
        print(f"Error checking for updates: {str(e)}")
        return jsonify({'has_updates': False})

    return jsonify({'has_updates': has_updates})

# Finance Entry Form
@app.route('/finance-entry/<string:epv_id>', methods=['GET', 'POST'])
@login_required
def finance_entry(epv_id):
    # Check if user has Finance role
    if session.get('employee_role') != 'Finance':
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))

    # Get the EPV
    epv = EPV.query.filter_by(epv_id=epv_id).first_or_404()

    # Check if EPV is approved
    if epv.status != 'approved':
        flash('This expense has not been approved yet.', 'error')
        return redirect(url_for('finance_dashboard'))

    # Get the employee's database ID from their email
    employee = EmployeeDetails.query.filter_by(email=session.get('email')).first()
    if not employee:
        flash('Error: Could not find your user account.', 'error')
        return redirect(url_for('dashboard'))

    # Check if this EPV is being processed by someone else
    if epv.being_processed_by and epv.processing_started_at:
        # Calculate how long it's been since processing started
        current_time = datetime.now()
        time_diff = current_time - epv.processing_started_at
        minutes_diff = time_diff.total_seconds() / 60

        # Define a timeout period (e.g., 30 minutes)
        timeout_period = 30  # minutes

        # If it's been less than the timeout period and it's not this user
        if minutes_diff < timeout_period and epv.being_processed_by != employee.id:
            # Get the name of the person processing it
            processor = EmployeeDetails.query.get(epv.being_processed_by)
            processor_name = processor.name if processor else 'another user'

            # Show an error message
            flash(f'This expense is currently being processed by {processor_name}. Please try again later.', 'error')
            return redirect(url_for('finance_dashboard'))
        elif minutes_diff >= timeout_period:
            # If it's been longer than the timeout, clear the processing fields
            epv.being_processed_by = None
            epv.processing_started_at = None

    # Claim this EPV for processing
    epv.being_processed_by = employee.id
    epv.processing_started_at = datetime.now()
    db.session.commit()

    # Check if EPV is from an assigned city
    assigned_cities = CityAssignment.query.filter_by(
        employee_id=employee.id,
        is_active=True
    ).all()
    city_names = [assignment.city for assignment in assigned_cities]

    # For master invoices, check the city of the first sub-invoice
    if epv.invoice_type == 'master':
        sub_invoices = EPV.query.filter_by(master_invoice_id=epv.id).all()
        if sub_invoices:
            # First check if the sub-invoice has a city field
            if sub_invoices[0].city and sub_invoices[0].city not in city_names:
                flash('You are not assigned to process expenses from this city.', 'error')
                return redirect(url_for('finance_dashboard'))
            # If not, fall back to the cost center's city
            elif sub_invoices[0].cost_center and sub_invoices[0].cost_center.city not in city_names:
                flash('You are not assigned to process expenses from this city.', 'error')
                return redirect(url_for('finance_dashboard'))
    # For standard invoices, check the city directly
    else:
        # First check if the EPV has a city field
        if epv.city and epv.city not in city_names:
            flash('You are not assigned to process expenses from this city.', 'error')
            return redirect(url_for('finance_dashboard'))
        # If not, fall back to the cost center's city
        elif epv.cost_center and epv.cost_center.city not in city_names:
            flash('You are not assigned to process expenses from this city.', 'error')
            return redirect(url_for('finance_dashboard'))
        # For invoices without a city or cost center, allow processing
        elif not epv.city and not epv.cost_center:
            # This is likely a master invoice without a city or cost center
            pass

    if request.method == 'POST':
        # Create a new finance entry
        finance_entry = FinanceEntry(
            epv_id=epv.id,
            finance_user_id=employee.id,
            vendor_name=request.form.get('vendor_name'),
            journal_entry=request.form.get('journal_entry'),
            payment_voucher=request.form.get('payment_voucher'),
            amount=float(request.form.get('amount')),
            reason=request.form.get('reason'),
            fcra_status=request.form.get('fcra_status'),
            comments=request.form.get('comments'),
            # Transaction ID and Payment Date will be added after Finance Approver approval
            transaction_id=None,
            payment_date=None
        )

        # Update EPV status
        epv.finance_status = 'processed'

        # Release the claim on this EPV
        epv.being_processed_by = None
        epv.processing_started_at = None

        # Save to database
        db.session.add(finance_entry)
        db.session.commit()

        flash('Finance entry has been submitted for approval.', 'success')
        return redirect(url_for('finance_dashboard'))

    return render_template(
        'finance_entry.html',
        user=session.get('user_info'),
        epv=epv,
        today=datetime.now()
    )

# Finance Approval
@app.route('/finance-approval/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def finance_approval(entry_id):
    # Check if user has Finance Approver role
    if session.get('employee_role') != 'Finance Approver':
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))

    # Get the finance entry
    entry = FinanceEntry.query.get_or_404(entry_id)

    # Get the EPV and its cost center
    epv = entry.epv
    cost_center = epv.cost_center

    # Check if finance approver is assigned to this city
    # Get the employee's database ID from their email
    employee = EmployeeDetails.query.filter_by(email=session.get('email')).first()
    if not employee:
        flash('Error: Could not find your user account.', 'error')
        return redirect(url_for('dashboard'))

    assigned_cities = CityAssignment.query.filter_by(
        employee_id=employee.id,
        is_active=True
    ).all()
    city_names = [assignment.city for assignment in assigned_cities]

    # If finance approver has assigned cities, check if they can access this EPV
    if assigned_cities:
        # First check if the EPV has a city field
        if epv.city and epv.city not in city_names:
            flash('You are not assigned to approve expenses from this city.', 'error')
            return redirect(url_for('finance_dashboard'))
        # If not, fall back to the cost center's city
        elif cost_center and cost_center.city not in city_names:
            flash('You are not assigned to approve expenses from this city.', 'error')
            return redirect(url_for('finance_dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'approve':
            # Approve the entry
            entry.status = 'approved'
            entry.approver_id = employee.id
            entry.approved_on = datetime.now()

            # Don't change the EPV finance_status - it should remain 'processed'
            # entry.epv.finance_status = 'approved'

            flash('Finance entry has been approved.', 'success')
        elif action == 'reject':
            # Reject the entry
            entry.status = 'rejected'
            entry.approver_id = employee.id
            entry.rejection_reason = request.form.get('rejection_reason')

            # Don't change the EPV finance_status - it should remain 'processed'
            # entry.epv.finance_status = 'rejected'

            flash('Finance entry has been rejected.', 'success')

        # Save to database
        db.session.commit()
        return redirect(url_for('finance_dashboard'))

    return render_template(
        'finance_approval.html',
        user=session.get('user_info'),
        entry=entry,
        epv=entry.epv
    )

# City Assignment Management
@app.route('/city-assignments', methods=['GET', 'POST'])
@login_required
def city_assignments():
    # Check if user has Finance Approver role
    if session.get('employee_role') != 'Finance Approver':
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))

    # Get all finance personnel and finance approvers
    finance_personnel = EmployeeDetails.query.filter(
        EmployeeDetails.role.in_(['Finance', 'Finance Approver']),
        EmployeeDetails.is_active == True
    ).all()

    # Get all cities
    cities = db.session.query(CostCenter.city).distinct().all()
    city_names = [city[0] for city in cities if city[0]]

    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        city = request.form.get('city')

        # Check if assignment already exists
        existing_assignment = CityAssignment.query.filter_by(
            employee_id=employee_id,
            city=city,
            is_active=True
        ).first()

        if existing_assignment:
            flash(f'This employee is already assigned to {city}.', 'warning')
        else:
            # Get the current user's database ID
            current_user = EmployeeDetails.query.filter_by(email=session.get('email')).first()
            if not current_user:
                flash('Error: Could not find your user account.', 'error')
                return redirect(url_for('city_assignments'))

            # Create new assignment
            assignment = CityAssignment(
                employee_id=employee_id,
                city=city,
                assigned_by=current_user.id if current_user else None
            )
            db.session.add(assignment)
            db.session.commit()

            flash(f'Employee has been assigned to {city}.', 'success')

        return redirect(url_for('city_assignments'))

    # Get all current assignments
    assignments = CityAssignment.query.filter_by(is_active=True).all()

    return render_template(
        'city_assignments.html',
        user=session.get('user_info'),
        finance_personnel=finance_personnel,
        cities=city_names,
        assignments=assignments
    )

# Update Payment Details
@app.route('/update-payment-details/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def update_payment_details(entry_id):
    # Check if user has Finance role
    if session.get('employee_role') != 'Finance':
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))

    # Get the finance entry
    entry = FinanceEntry.query.get_or_404(entry_id)

    # Check if the entry is approved
    if entry.status != 'approved':
        flash('You can only update payment details for approved entries.', 'error')
        return redirect(url_for('finance_dashboard'))

    # Check if the entry was processed by this user
    employee = EmployeeDetails.query.filter_by(email=session.get('email')).first()
    if not employee or entry.finance_user_id != employee.id:
        flash('You can only update payment details for entries you processed.', 'error')
        return redirect(url_for('finance_dashboard'))

    # Import the processing days calculation function
    from utils import calculate_processing_days

    if request.method == 'POST':
        # Update the payment details
        entry.transaction_id = request.form.get('transaction_id')

        # Parse the payment date
        payment_date_str = request.form.get('payment_date')
        if payment_date_str:
            try:
                entry.payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')

                # Calculate processing days after setting the payment date
                processing_days = calculate_processing_days(entry.epv, entry)

                # Get the max processing days from settings
                max_days = 5  # Default value
                setting = SettingsFinance.query.filter_by(setting_name='max_days_processing').first()
                if setting:
                    try:
                        max_days = int(setting.setting_value)
                    except (ValueError, TypeError):
                        pass

                # Show a message about processing days
                if processing_days > 0:
                    if processing_days > max_days:
                        flash(f'Warning: Processing took {processing_days} days, which exceeds the SOP of {max_days} days.', 'warning')
                    else:
                        flash(f'Processing completed in {processing_days} business days.', 'info')

            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
                return redirect(url_for('update_payment_details', entry_id=entry_id))

        # Save to database
        db.session.commit()

        flash('Payment details have been updated.', 'success')
        return redirect(url_for('finance_dashboard'))

    # Calculate processing days for display
    processing_days = 0
    if entry.payment_date:
        processing_days = calculate_processing_days(entry.epv, entry)

    # Get the max processing days from settings
    max_days = 5  # Default value
    setting = SettingsFinance.query.filter_by(setting_name='max_days_processing').first()
    if setting:
        try:
            max_days = int(setting.setting_value)
        except (ValueError, TypeError):
            pass

    return render_template(
        'update_payment_details.html',
        user=session.get('user_info'),
        entry=entry,
        epv=entry.epv,
        processing_days=processing_days,
        max_days=max_days
    )

# Toggle City Assignment Status
@app.route('/city-assignment/<int:assignment_id>/toggle', methods=['POST'])
@login_required
def toggle_city_assignment(assignment_id):
    # Check if user has Finance Approver role
    if session.get('employee_role') != 'Finance Approver':
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('dashboard'))

    # Get the assignment
    assignment = CityAssignment.query.get_or_404(assignment_id)

    # Toggle the status
    assignment.is_active = not assignment.is_active
    db.session.commit()

    if assignment.is_active:
        flash(f'Assignment has been activated.', 'success')
    else:
        flash(f'Assignment has been deactivated.', 'success')

    return redirect(url_for('city_assignments'))

if __name__ == '__main__':
    # Allow OAuth without HTTPS for local development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Print debug information
    print("DEBUG: Starting application with the following configuration:")
    print(f"DEBUG: GOOGLE_CLIENT_ID: {os.environ.get('GOOGLE_CLIENT_ID')}")
    print(f"DEBUG: OAUTHLIB_INSECURE_TRANSPORT: {os.environ.get('OAUTHLIB_INSECURE_TRANSPORT')}")

    # Initialize the database
    with app.app_context():
        # Don't drop all tables to preserve EPV records
        # db.drop_all()
        db.create_all()
        init_db(app)

        # Add new columns to finance_entry table if they don't exist
        try:
            # Check if transaction_id column exists
            db.session.execute(db.text("SELECT transaction_id FROM finance_entry LIMIT 1"))
            print("transaction_id column already exists in finance_entry table")
        except Exception as e:
            if "Unknown column" in str(e):
                print("Adding transaction_id column to finance_entry table")
                db.session.execute(db.text("ALTER TABLE finance_entry ADD COLUMN transaction_id VARCHAR(100) NULL"))
                db.session.commit()

        try:
            # Check if payment_date column exists
            db.session.execute(db.text("SELECT payment_date FROM finance_entry LIMIT 1"))
            print("payment_date column already exists in finance_entry table")
        except Exception as e:
            if "Unknown column" in str(e):
                print("Adding payment_date column to finance_entry table")
                db.session.execute(db.text("ALTER TABLE finance_entry ADD COLUMN payment_date DATETIME NULL"))
                db.session.commit()

        # Check if city column exists in EPV table
        try:
            # Check if city column exists
            db.session.execute(db.text("SELECT city FROM epv LIMIT 1"))
            print("city column already exists in epv table")
        except Exception as e:
            if "Unknown column" in str(e):
                print("Adding city column to epv table")
                db.session.execute(db.text("ALTER TABLE epv ADD COLUMN city VARCHAR(50) NULL"))
                db.session.commit()

    # Only run the app when this file is executed directly, not when imported
    if __name__ == '__main__':
        # Always use port 5000 as requested
        # In development, you can use debug mode
        # In production, debug should be False
        debug_mode = os.environ.get('FLASK_ENV') == 'development'
        app.run(host='127.0.0.1', port=5000, debug=debug_mode)

# Make the Flask application available as 'application' for WSGI
application = app

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import traceback
from datetime import datetime

# Load environment variables
load_dotenv()

def create_message(sender, to, subject, html_content):
    """Create a message for an email."""
    message = MIMEMultipart('alternative')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Attach HTML content
    html_part = MIMEText(html_content, 'html')
    message.attach(html_part)

    # Encode the message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return {'raw': encoded_message}

def send_message(credentials, sender, to, subject, html_content):
    """Send an email message."""
    print(f"DEBUG: send_message called with sender: {sender}, to: {to}, subject: {subject}")
    try:
        # Build the Gmail service
        print(f"DEBUG: Building Gmail service with credentials")
        print(f"DEBUG: Credentials type: {type(credentials).__name__}")

        # Validate credentials
        if not hasattr(credentials, 'token') or not credentials.token:
            print("ERROR: Invalid credentials - missing token")
            return False, "Invalid credentials - missing token"

        print(f"DEBUG: Credentials token: {credentials.token[:10]}... (truncated)")
        print(f"DEBUG: Credentials has refresh token: {'Yes' if hasattr(credentials, 'refresh_token') and credentials.refresh_token else 'No'}")
        print(f"DEBUG: Credentials scopes: {credentials.scopes if hasattr(credentials, 'scopes') else 'No scopes'}")

        # Build the service
        service = build('gmail', 'v1', credentials=credentials)
        print(f"DEBUG: Successfully built Gmail service")

        # Create the message
        print(f"DEBUG: Creating message")
        message = create_message(sender, to, subject, html_content)
        print(f"DEBUG: Successfully created message")

        # Send the message
        print(f"DEBUG: Sending message")
        sent_message = service.users().messages().send(userId="me", body=message).execute()
        print(f"DEBUG: Message sent successfully. Message ID: {sent_message['id']}")
        return True, sent_message['id']

    except HttpError as error:
        print(f"ERROR: An HTTP error occurred while sending the email: {error}")
        error_details = str(error)
        if 'invalid_grant' in error_details.lower():
            print("ERROR: Invalid grant error - token may be expired or revoked")
        elif '401' in error_details:
            print("ERROR: 401 Unauthorized - authentication failed")
        elif '403' in error_details:
            print("ERROR: 403 Forbidden - insufficient permissions")
        print(f"DEBUG: HTTP error details: {error_details}")
        print(f"DEBUG: HTTP error traceback: {traceback.format_exc()}")
        return False, error_details
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        print(f"DEBUG: Unexpected error traceback: {traceback.format_exc()}")
        return False, str(e)

def create_approval_email(epv_record, sender_email, base_url, token=None):
    """Create an HTML email for expense approval."""
    # Format expense details
    expense_date_range = f"{epv_record.from_date.strftime('%d-%m-%Y') if hasattr(epv_record.from_date, 'strftime') else epv_record.from_date} to {epv_record.to_date.strftime('%d-%m-%Y') if hasattr(epv_record.to_date, 'strftime') else epv_record.to_date}" if epv_record.from_date and epv_record.to_date else "N/A"
    total_amount = f"₹{epv_record.total_amount:.2f}" if epv_record.total_amount else "N/A"

    # Get expense items
    expense_items = epv_record.items

    # Create approval and rejection URLs with token if provided
    if token:
        approve_url = f"{base_url}/approve-expense/{epv_record.epv_id}?token={token}"
        reject_url = f"{base_url}/reject-expense/{epv_record.epv_id}?token={token}"
        view_url = f"{base_url}/epv-record/{epv_record.epv_id}?token={token}"
    else:
        # Fallback to legacy URLs without token
        approve_url = f"{base_url}/approve-expense/{epv_record.epv_id}"
        reject_url = f"{base_url}/reject-expense/{epv_record.epv_id}"
        view_url = f"{base_url}/epv-record/{epv_record.epv_id}"

    # Create HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Expense Approval Request</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #3f51b5;
                color: white;
                padding: 15px;
                border-radius: 5px 5px 0 0;
                text-align: center;
            }}
            .content {{
                padding: 20px;
                border: 1px solid #ddd;
                border-top: none;
                border-radius: 0 0 5px 5px;
            }}
            .expense-details {{
                margin-bottom: 20px;
            }}
            .expense-details table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .expense-details th, .expense-details td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}
            .expense-details th {{
                border: 1px solid #ddd;
                font-weight: bold;
                background-color: #f5f5f5;
            }}
            .expense-details tfoot {{
                font-weight: bold;
                background-color: #f5f5f5;
            }}
            .expense-details thead {{
                background-color: #f5f5f5;
                color: black;
            }}
            .buttons {{
                margin-top: 30px;
                text-align: center;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                margin: 0 10px;
                border-radius: 5px;
                text-decoration: none;
                font-weight: bold;
                color: white;
            }}
            .approve {{
                background-color: #4CAF50;
            }}
            .reject {{
                background-color: #f44336;
            }}
            .view {{
                background-color: #2196F3;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #777;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Expense Approval Request</h2>
        </div>
        <div class="content">
            <p>Dear Approver,</p>
            <p>An expense voucher has been submitted for your approval. Please review the details below:</p>

            <div class="expense-details">
                <table>
                    <tr>
                        <th>EPV ID</th>
                        <td>{epv_record.epv_id}</td>
                    </tr>
                    <tr>
                        <th>Employee</th>
                        <td>{epv_record.employee_name} ({epv_record.employee_id})</td>
                    </tr>
                    <tr>
                        <th>Date Range</th>
                        <td>{expense_date_range}</td>
                    </tr>
                    <tr>
                        <th>Total Amount</th>
                        <td>{total_amount}</td>
                    </tr>
                    <tr>
                        <th>Submitted On</th>
                        <td>{epv_record.submission_date.strftime('%d-%m-%Y') if epv_record.submission_date else 'N/A'}</td>
                    </tr>
                </table>
            </div>

            <h3>Expense Items</h3>
            <div class="expense-details">
                <table>
                    <thead>
                        <tr>
                            <th>Invoice Date</th>
                            <th>Expense Head</th>
                            <th>Description</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join([f"<tr><td>{item.expense_invoice_date.strftime('%d-%m-%Y') if hasattr(item.expense_invoice_date, 'strftime') else item.expense_invoice_date}</td><td>{item.expense_head}</td><td>{item.description}</td><td>₹{item.amount:.2f}</td></tr>" for item in expense_items])}
                    </tbody>
                    <tfoot>
                        <tr>
                            <th colspan="3" style="text-align: right;">Total:</th>
                            <th>{total_amount}</th>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div class="buttons">
                <a href="{view_url}" class="button view">View Details</a>
            </div>

            <p>To approve or reject this expense, please click the "View Details" button above and use the approval options in the system.</p>

            <p>If you have any questions, please contact the submitter at {epv_record.email_id}.</p>

            <div class="footer">
                <p>This is an automated email from the Expense Management System. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html_content

def create_rejection_notification_email(epv_record, sender_email, rejected_by, rejection_reason):
    """Create an HTML email to notify the submitter that their expense was rejected."""
    # Format expense details
    expense_date_range = f"{epv_record.from_date.strftime('%d-%m-%Y') if hasattr(epv_record.from_date, 'strftime') else epv_record.from_date} to {epv_record.to_date.strftime('%d-%m-%Y') if hasattr(epv_record.to_date, 'strftime') else epv_record.to_date}" if epv_record.from_date and epv_record.to_date else "N/A"
    total_amount = f"Rs. {epv_record.total_amount:.2f}" if epv_record.total_amount else "N/A"

    # Get expense items
    expense_items = epv_record.items

    # Create HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Expense Rejection Notification</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #f44336;
                color: white;
                padding: 15px;
                border-radius: 5px 5px 0 0;
                text-align: center;
            }}
            .content {{
                padding: 20px;
                border: 1px solid #ddd;
                border-top: none;
                border-radius: 0 0 5px 5px;
            }}
            .expense-details {{
                margin-bottom: 20px;
            }}
            .expense-details table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .expense-details th, .expense-details td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}
            .expense-details th {{
                border: 1px solid #ddd;
                font-weight: bold;
                background-color: #f5f5f5;
            }}
            .rejection-reason {{
                margin-top: 20px;
                padding: 15px;
                background-color: #fff9f9;
                border-left: 4px solid #f44336;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #777;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Expense Rejection Notification</h2>
        </div>
        <div class="content">
            <p>Dear {epv_record.employee_name},</p>
            <p>We regret to inform you that your expense voucher has been rejected. Please review the details below:</p>

            <div class="expense-details">
                <table>
                    <tr>
                        <th>EPV ID</th>
                        <td>{epv_record.epv_id}</td>
                    </tr>
                    <tr>
                        <th>Date Range</th>
                        <td>{expense_date_range}</td>
                    </tr>
                    <tr>
                        <th>Total Amount</th>
                        <td>{total_amount}</td>
                    </tr>
                    <tr>
                        <th>Rejected By</th>
                        <td>{rejected_by}</td>
                    </tr>
                    <tr>
                        <th>Rejected On</th>
                        <td>{datetime.now().strftime('%d-%m-%Y %H:%M')}</td>
                    </tr>
                </table>
            </div>

            <div class="rejection-reason">
                <h3>Reason for Rejection:</h3>
                <p>{rejection_reason}</p>
            </div>

            <p>Please make the necessary corrections and resubmit your expense voucher if needed.</p>
            <p>If you have any questions, please contact your manager or the finance team.</p>

            <div class="footer">
                <p>This is an automated email from the Expense Management System. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html_content

def send_rejection_notification_email(epv_record, credentials, rejected_by, rejection_reason):
    """Send a rejection notification email to the expense submitter."""
    print(f"DEBUG: send_rejection_notification_email called with EPV ID: {epv_record.epv_id}")

    # Validate credentials
    if not credentials:
        print("ERROR: No credentials provided for sending email")
        return False, "No credentials provided"

    # Check if credentials has the necessary attributes
    if not hasattr(credentials, 'token') or not credentials.token:
        print("ERROR: Invalid credentials - missing token")
        return False, "Invalid credentials - missing token"

    # Get sender email from credentials or use a default
    sender_email = "expense.system@akanksha.org"
    print(f"DEBUG: Using sender email: {sender_email}")

    # Get recipient email (the submitter)
    recipient_email = epv_record.email_id
    if not recipient_email:
        print("ERROR: No recipient email found in EPV record")
        return False, "No recipient email found"

    # Create email subject
    subject = f"Expense Rejection Notification: {epv_record.epv_id}"
    print(f"DEBUG: Email subject: {subject}")

    # Create HTML content for the rejection notification
    try:
        html_content = create_rejection_notification_email(epv_record, sender_email, rejected_by, rejection_reason)
        print(f"DEBUG: Created HTML content for rejection email, length: {len(html_content)}")
    except Exception as e:
        print(f"ERROR creating HTML content: {str(e)}")
        print(f"DEBUG: HTML content traceback: {traceback.format_exc()}")
        return False, f"Error creating email content: {str(e)}"

    # Send the email
    try:
        print(f"DEBUG: Sending rejection notification email to {recipient_email}")
        print(f"DEBUG: Credentials token: {credentials.token[:10]}... (truncated)")
        print(f"DEBUG: Credentials has refresh token: {'Yes' if hasattr(credentials, 'refresh_token') and credentials.refresh_token else 'No'}")
        print(f"DEBUG: Credentials scopes: {credentials.scopes}")

        result = send_message(credentials, sender_email, recipient_email, subject, html_content)
        print(f"DEBUG: Email send result: {result}")
        return result
    except Exception as e:
        print(f"ERROR sending email: {str(e)}")
        print(f"DEBUG: Email sending traceback: {traceback.format_exc()}")
        return False, f"Error sending email: {str(e)}"

def send_email(to, subject, html_content, sender="expense.system@akanksha.org"):
    """Send an email using the Google API with credentials from the session."""
    from flask import session

    # Check if we have Google token in session
    if 'google_token' not in session:
        print("ERROR: No Google token in session")
        return False, "No Google token in session"

    # Create credentials from session token
    try:
        credentials = Credentials(
            token=session['google_token']['access_token'],
            refresh_token=session['google_token']['refresh_token'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
    except Exception as e:
        print(f"ERROR creating credentials: {str(e)}")
        return False, f"Error creating credentials: {str(e)}"

    # Send the email using the send_message function
    return send_message(credentials, sender, to, subject, html_content)

def send_document_request_email(epv_record, requested_docs):
    """Send an email to notify the user that additional documents have been requested."""
    # Get the recipient email (the submitter)
    recipient_email = epv_record.email_id
    if not recipient_email:
        print("ERROR: No recipient email found in EPV record")
        return False, "No recipient email found"

    # Create email subject
    subject = f"Additional Documents Requested: {epv_record.epv_id}"

    # Create HTML content for the email
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Additional Documents Requested</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #ff9800;
                color: white;
                padding: 15px;
                border-radius: 5px 5px 0 0;
                text-align: center;
            }}
            .content {{
                padding: 20px;
                border: 1px solid #ddd;
                border-top: none;
                border-radius: 0 0 5px 5px;
            }}
            .requested-docs {{
                margin-top: 20px;
                padding: 15px;
                background-color: #fff9e6;
                border-left: 4px solid #ff9800;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #777;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Additional Documents Requested</h2>
        </div>
        <div class="content">
            <p>Dear {epv_record.employee_name},</p>
            <p>The finance team has reviewed your expense voucher and is requesting additional documents to process it.</p>

            <div class="requested-docs">
                <h3>Requested Documents:</h3>
                <p>{requested_docs}</p>
            </div>

            <p>Please upload the requested documents as soon as possible to avoid delays in processing your expense.</p>
            <p>You can upload the documents by logging into the Expense Management System and viewing your EPV record.</p>

            <div class="footer">
                <p>This is an automated email from the Expense Management System. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Send the email
    return send_email(to=recipient_email, subject=subject, html_content=html_content)

def send_approval_email(epv_record, approver_email, credentials, base_url, token=None):
    """Send an approval email for an expense record."""
    print(f"DEBUG: send_approval_email called with EPV ID: {epv_record.epv_id}, approver: {approver_email}")

    # Validate credentials
    if not credentials:
        print("ERROR: No credentials provided for sending email")
        return False, "No credentials provided"

    # Check if credentials has the necessary attributes
    if not hasattr(credentials, 'token') or not credentials.token:
        print("ERROR: Invalid credentials - missing token")
        return False, "Invalid credentials - missing token"

    # Get sender email from credentials or use a default
    sender_email = "expense.system@akanksha.org"
    print(f"DEBUG: Using sender email: {sender_email}")

    # Create email subject
    subject = f"Expense Approval Request: {epv_record.epv_id}"
    print(f"DEBUG: Email subject: {subject}")

    # Create HTML content with token for secure approval/rejection
    try:
        html_content = create_approval_email(epv_record, sender_email, base_url, token)
        print(f"DEBUG: Created HTML content for email, length: {len(html_content)}")
    except Exception as e:
        print(f"ERROR creating HTML content: {str(e)}")
        print(f"DEBUG: HTML content traceback: {traceback.format_exc()}")
        return False, f"Error creating email content: {str(e)}"

    # Send the email
    try:
        print(f"DEBUG: Sending email to {approver_email}")
        print(f"DEBUG: Credentials token: {credentials.token[:10]}... (truncated)")
        print(f"DEBUG: Credentials has refresh token: {'Yes' if hasattr(credentials, 'refresh_token') and credentials.refresh_token else 'No'}")
        print(f"DEBUG: Credentials scopes: {credentials.scopes}")

        result = send_message(credentials, sender_email, approver_email, subject, html_content)
        print(f"DEBUG: Email send result: {result}")
        return result
    except Exception as e:
        print(f"ERROR sending email: {str(e)}")
        print(f"DEBUG: Email sending traceback: {traceback.format_exc()}")
        return False, f"Error sending email: {str(e)}"

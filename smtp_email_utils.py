import os
import smtplib
import traceback
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

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

    return message

def send_message(sender, to, subject, html_content):
    """Send an email message using SMTP."""
    print(f"DEBUG: send_message called with sender: {sender}, to: {to}, subject: {subject}")
    try:
        # Get SMTP settings from environment variables
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')

        print(f"DEBUG: SMTP Settings - Server: {smtp_server}, Port: {smtp_port}, Username: {smtp_username}")

        # Validate SMTP settings
        if not smtp_username or not smtp_password:
            error_msg = "SMTP credentials not found in environment variables"
            print(f"ERROR: {error_msg}")
            return False, error_msg

        # Create the message
        print(f"DEBUG: Creating message")
        message = create_message(sender, to, subject, html_content)
        print(f"DEBUG: Successfully created message")

        # Connect to SMTP server
        print(f"DEBUG: Connecting to SMTP server {smtp_server}:{smtp_port}")
        try:
            # Check if we should use SSL (port 465) or TLS (port 587)
            if smtp_port == 465:
                # Use SSL
                print(f"DEBUG: Using SSL connection")
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            else:
                # Use TLS
                print(f"DEBUG: Using TLS connection")
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)

            print(f"DEBUG: Successfully connected to SMTP server")

            # Set debug level to see detailed SMTP communication
            server.set_debuglevel(1)

            # Only use TLS and authentication for real SMTP servers, not for local debugging
            if smtp_server != 'localhost':
                print(f"DEBUG: Sending EHLO command")
                server.ehlo()

                # If using TLS (not SSL), start TLS
                if smtp_port != 465:
                    print(f"DEBUG: Starting TLS")
                    server.starttls()
                    print(f"DEBUG: Sending EHLO command again after TLS")
                    server.ehlo()

                # Login to SMTP server - try different authentication methods
                print(f"DEBUG: Logging in to SMTP server with username: {smtp_username}")
                try:
                    # Try standard login
                    server.login(smtp_username, smtp_password)
                    print(f"DEBUG: Successfully logged in to SMTP server")
                except smtplib.SMTPAuthenticationError as auth_error:
                    print(f"DEBUG: Standard login failed, trying alternative authentication")
                    # If we're using Gmail, we can try a different approach
                    if 'gmail' in smtp_server:
                        try:
                            # Try plain auth
                            server.docmd("AUTH", "PLAIN " + base64.b64encode(f"\0{smtp_username}\0{smtp_password}".encode()).decode())
                            print(f"DEBUG: Successfully logged in using PLAIN auth")
                        except Exception as plain_error:
                            print(f"DEBUG: PLAIN auth failed: {plain_error}")
                            # Try login auth
                            try:
                                server.docmd("AUTH", "LOGIN")
                                server.docmd(base64.b64encode(smtp_username.encode()).decode())
                                server.docmd(base64.b64encode(smtp_password.encode()).decode())
                                print(f"DEBUG: Successfully logged in using LOGIN auth")
                            except Exception as login_error:
                                print(f"DEBUG: LOGIN auth failed: {login_error}")
                                # Re-raise the original error if all methods fail
                                raise auth_error
                    else:
                        # Re-raise the original error for non-Gmail servers
                        raise auth_error
            else:
                print(f"DEBUG: Using local debugging server, skipping authentication")

            # Send the message
            print(f"DEBUG: Sending message from {sender} to {to}")
            server.sendmail(sender, to, message.as_string())
            print(f"DEBUG: Message sent successfully")

            # Close the connection
            print(f"DEBUG: Closing SMTP connection")
            server.quit()
            print(f"DEBUG: SMTP connection closed")

            return True, "Message sent successfully"
        except smtplib.SMTPConnectError as connect_error:
            error_msg = f"SMTP Connection Error: {connect_error}"
            print(f"ERROR: {error_msg}")
            return False, error_msg
        except smtplib.SMTPHeloError as helo_error:
            error_msg = f"SMTP HELO Error: {helo_error}"
            print(f"ERROR: {error_msg}")
            return False, error_msg
        except smtplib.SMTPException as smtp_error:
            error_msg = f"SMTP Error: {smtp_error}"
            print(f"ERROR: {error_msg}")
            return False, error_msg

    except smtplib.SMTPAuthenticationError as error:
        error_msg = f"SMTP Authentication Error: {error}"
        print(f"ERROR: {error_msg}")
        print(f"DEBUG: SMTP error traceback: {traceback.format_exc()}")
        return False, error_msg
    except smtplib.SMTPException as error:
        error_msg = f"SMTP Error: {error}"
        print(f"ERROR: {error_msg}")
        print(f"DEBUG: SMTP error traceback: {traceback.format_exc()}")
        return False, error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(f"ERROR: {error_msg}")
        print(f"DEBUG: Unexpected error traceback: {traceback.format_exc()}")
        return False, error_msg

def create_approval_email(epv_record, sender_email, base_url, token=None):
    """Create an HTML email for expense approval."""
    # Format expense details
    expense_date_range = f"{epv_record.from_date.strftime('%d-%m-%Y') if hasattr(epv_record.from_date, 'strftime') else epv_record.from_date} to {epv_record.to_date.strftime('%d-%m-%Y') if hasattr(epv_record.to_date, 'strftime') else epv_record.to_date}" if epv_record.from_date and epv_record.to_date else "N/A"
    total_amount = f"₹{epv_record.total_amount:.2f}" if epv_record.total_amount else "N/A"

    # Get expense items
    expense_items = epv_record.items

    # Create HTML content with inline styles for better email client compatibility
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expense Approval Request</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd;">
        <div style="background-color: #f8f9fa; padding: 15px; text-align: center; border-bottom: 2px solid #007bff;">
            <h2 style="margin: 0; color: #007bff;">Expense Approval Request</h2>
        </div>
        <div style="padding: 20px;">
            <p>Dear Approver,</p>
            <p>An expense voucher has been submitted for your approval. Please review the details below:</p>

            <div style="margin-bottom: 20px;">
                <h3 style="border-bottom: 1px solid #ddd; padding-bottom: 5px; color: #555;">Expense Details</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2; width: 30%;">EPV ID</th>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{epv_record.epv_id}</td>
                    </tr>
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Employee</th>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{epv_record.employee_name}</td>
                    </tr>
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Cost Center</th>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{epv_record.cost_center.costcenter if epv_record.cost_center else 'N/A'}</td>
                    </tr>
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Date Range</th>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{expense_date_range}</td>
                    </tr>
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Total Amount</th>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{total_amount}</td>
                    </tr>
                </table>
            </div>

            <div style="margin-bottom: 20px;">
                <h3 style="border-bottom: 1px solid #ddd; padding-bottom: 5px; color: #555;">Expense Items</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Date</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Description</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Category</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Amount</th>
                    </tr>
                    {''.join([f"""<tr>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{item.expense_invoice_date.strftime('%d-%m-%Y') if hasattr(item.expense_invoice_date, 'strftime') else item.expense_invoice_date}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{item.description}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{item.expense_head}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">₹{item.amount:.2f}</td>
                    </tr>""" for item in expense_items])}
                </table>
            </div>

            <p>To view the complete expense details and attached receipts, please click the button below:</p>

            <div style="margin-top: 20px; text-align: center;">
                <a href="{base_url}/epv-record/{epv_record.epv_id}?token={token}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">View Details</a>
            </div>

            <p style="margin-top: 20px;">Thank you for your attention to this matter.</p>

            <p>Best regards,<br>Expense Management System</p>
        </div>

        <div style="margin-top: 30px; font-size: 12px; color: #777; text-align: center; border-top: 1px solid #ddd; padding-top: 10px;">
            <p>This is an automated email from the Expense Management System. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>"""

    return html_content

def create_rejection_notification_email(epv_record, sender_email, rejected_by, rejection_reason):
    """Create an HTML email to notify the submitter that their expense was rejected."""
    # Format expense details
    expense_date_range = f"{epv_record.from_date.strftime('%d-%m-%Y') if hasattr(epv_record.from_date, 'strftime') else epv_record.from_date} to {epv_record.to_date.strftime('%d-%m-%Y') if hasattr(epv_record.to_date, 'strftime') else epv_record.to_date}" if epv_record.from_date and epv_record.to_date else "N/A"
    total_amount = f"Rs. {epv_record.total_amount:.2f}" if epv_record.total_amount else "N/A"

    # Create HTML content with inline styles for better email client compatibility
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expense Rejection Notification</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd;">
        <div style="background-color: #f8f9fa; padding: 15px; text-align: center; border-bottom: 2px solid #dc3545;">
            <h2 style="margin: 0; color: #dc3545;">Expense Rejection Notification</h2>
        </div>
        <div style="padding: 20px;">
            <p>Dear {epv_record.employee_name},</p>
            <p>We regret to inform you that your expense voucher has been rejected by <strong>{rejected_by}</strong>.</p>

            <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #856404;">Rejection Reason:</h3>
                <p style="margin-bottom: 0;">{rejection_reason}</p>
            </div>

            <div style="margin-bottom: 20px;">
                <h3 style="border-bottom: 1px solid #ddd; padding-bottom: 5px; color: #555;">Expense Details</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2; width: 30%;">EPV ID</th>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{epv_record.epv_id}</td>
                    </tr>
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Date Range</th>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{expense_date_range}</td>
                    </tr>
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Total Amount</th>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: left;">{total_amount}</td>
                    </tr>
                </table>
            </div>

            <p>You may need to resubmit your expense with the necessary corrections or additional information.</p>

            <div style="margin-top: 20px; text-align: center;">
                <a href="{epv_record.file_url}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">View Expense Document</a>
            </div>

            <p style="margin-top: 20px;">If you have any questions, please contact your manager or the finance team.</p>

            <p>Best regards,<br>Expense Management System</p>
        </div>

        <div style="margin-top: 30px; font-size: 12px; color: #777; text-align: center; border-top: 1px solid #ddd; padding-top: 10px;">
            <p>This is an automated email from the Expense Management System. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>"""

    return html_content

def send_approval_email(epv_record, approver_email, base_url, token=None):
    """Send an approval email for an expense record."""
    print(f"DEBUG: send_approval_email called with EPV ID: {epv_record.epv_id}, approver: {approver_email}")

    # Get sender email from environment or use a default
    sender_email = os.environ.get('SMTP_USERNAME', "expense.system@akanksha.org")
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
        result = send_message(sender_email, approver_email, subject, html_content)
        print(f"DEBUG: Email send result: {result}")
        return result
    except Exception as e:
        print(f"ERROR sending email: {str(e)}")
        print(f"DEBUG: Email sending traceback: {traceback.format_exc()}")
        return False, f"Error sending email: {str(e)}"

def send_rejection_notification_email(epv_record, rejected_by, rejection_reason):
    """Send a rejection notification email to the expense submitter."""
    print(f"DEBUG: send_rejection_notification_email called with EPV ID: {epv_record.epv_id}")

    # Get recipient email
    recipient_email = epv_record.email_id
    if not recipient_email:
        print("ERROR: No recipient email found in EPV record")
        return False, "No recipient email found"

    # Get sender email from environment or use a default
    sender_email = os.environ.get('SMTP_USERNAME', "expense.system@akanksha.org")
    print(f"DEBUG: Using sender email: {sender_email}")

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
        result = send_message(sender_email, recipient_email, subject, html_content)
        print(f"DEBUG: Email send result: {result}")
        return result
    except Exception as e:
        print(f"ERROR sending email: {str(e)}")
        print(f"DEBUG: Email sending traceback: {traceback.format_exc()}")
        return False, f"Error sending email: {str(e)}"

def send_email(to, subject, html_content, sender=None):
    """Send an email using SMTP."""
    # Get sender email from environment or use the provided sender
    sender_email = sender or os.environ.get('SMTP_USERNAME', "expense.system@akanksha.org")

    # Send the email using the send_message function
    return send_message(sender_email, to, subject, html_content)

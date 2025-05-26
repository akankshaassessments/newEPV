# EPV (Expense Payment Voucher) Management System

A comprehensive web-based expense management system built with Flask for managing employee expense vouchers, approvals, and payments.

## Features

### Core Functionality
- **Employee Expense Submission**: Submit expense vouchers with multiple expense items
- **Manager Approval**: Email-based approval system (no login required for managers)
- **Finance Processing**: Finance team can process, approve, and manage payments
- **Document Management**: Upload receipts and supplementary documents
- **PDF Generation**: Automatic PDF generation for expense vouchers
- **Google Drive Integration**: Automatic upload to Google Drive

### User Roles
- **Regular Users**: Submit and track their own expenses
- **Managers**: Approve/reject team member expenses via email
- **Cost Center Approvers**: Manage expenses for specific cost centers
- **Finance Personnel**: Process approved expenses and enter payment details
- **Finance Approvers**: Final approval for finance entries
- **Super Admin**: Full system access and configuration

### Advanced Features
- **Split Invoice Support**: Handle master invoices with sub-invoices
- **City-based Assignment**: Finance users assigned to specific cities
- **Processing Time Tracking**: Monitor expense processing efficiency
- **Email Notifications**: SMTP-based email system for all notifications
- **Supplementary Documents**: Upload additional documents after rejection
- **Real-time Dashboard**: Finance dashboard with live updates

## Technology Stack

- **Backend**: Python Flask
- **Database**: MySQL
- **Authentication**: Google OAuth 2.0
- **Email**: SMTP (Gmail)
- **PDF Processing**: ReportLab, PyPDF2
- **File Storage**: Google Drive API
- **Frontend**: HTML, CSS, JavaScript, Bootstrap

## Installation

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- Google Cloud Project with OAuth 2.0 credentials
- Gmail account for SMTP

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd EPV
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database Setup**
   ```bash
   # Create MySQL database
   mysql -u root -p
   CREATE DATABASE AFDW;
   ```

5. **Environment Configuration**
   ```bash
   # Copy environment template
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Initialize Database**
   ```bash
   python app.py
   # Database tables will be created automatically
   ```

## Configuration

### Environment Variables (.env)

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Flask Configuration
FLASK_SECRET_KEY=your-secret-key
FLASK_ENV=development  # or production

# Database Configuration
DB_HOST=localhost
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_NAME=AFDW
DB_PORT=3306

# SMTP Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API and Drive API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `http://localhost:5000/login/google/authorized` (development)
   - `https://yourdomain.com/login/google/authorized` (production)

### Gmail SMTP Setup

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password
3. Use the App Password in SMTP_PASSWORD

## Deployment

### Production Deployment (cPanel)

1. **Upload files to server**
   ```bash
   # Upload all files except uploads/, venv/, __pycache__/
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt --user
   ```

3. **Configure passenger_wsgi.py**
   ```python
   import os
   import sys
   sys.path.insert(0, os.path.dirname(__file__))
   from app import application
   ```

4. **Set environment variables**
   - Update .env with production values
   - Set FLASK_ENV=production

5. **Database Migration**
   - Import database schema
   - Update connection settings

### Server Requirements

- Python 3.8+
- MySQL 5.7+
- SSL Certificate (for production)
- Sufficient storage for file uploads

## Usage

### For Employees
1. Login with Google account
2. Submit new expense voucher
3. Upload receipts and documents
4. Track approval status

### For Managers
1. Receive email notification
2. Click approve/reject link in email
3. Provide rejection reason if needed

### For Finance Team
1. Login to finance dashboard
2. Process approved expenses
3. Enter payment details
4. Generate reports

## API Documentation

### Key Endpoints

- `POST /submit-expense` - Submit new expense
- `GET /epv-records` - View expense records
- `POST /send-for-approval` - Send for manager approval
- `GET /approve-expense/<epv_id>` - Approve expense (token-based)
- `GET /finance-dashboard` - Finance dashboard
- `POST /finance-entry` - Process finance entry

## Database Schema

### Key Tables
- `employee_details` - User information and roles
- `epv` - Main expense voucher records
- `epv_item` - Individual expense items
- `epv_approval` - Approval tracking
- `finance_entry` - Finance processing records
- `cost_center` - Cost center configuration
- `city_assignment` - Finance user city assignments

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## Support

For technical support or questions:
- Create an issue in the repository
- Contact the development team

## License

This project is proprietary software developed for Akanksha Foundation.

## Version History

- v1.0 - Initial release with basic expense management
- v1.1 - Added split invoice support
- v1.2 - Enhanced finance dashboard and reporting
- v1.3 - Added supplementary documents feature
- v1.4 - Improved email system and notifications

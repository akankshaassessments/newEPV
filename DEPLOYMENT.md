# EPV System Deployment Guide

This guide covers deploying the EPV (Expense Payment Voucher) system to production.

## Pre-Deployment Checklist

### 1. Server Requirements
- **Python**: 3.8 or higher
- **MySQL**: 5.7 or higher
- **Web Server**: Apache/Nginx with WSGI support
- **SSL Certificate**: Required for production
- **Storage**: Minimum 10GB for file uploads
- **Memory**: Minimum 2GB RAM

### 2. Domain and SSL
- Domain name configured and pointing to server
- SSL certificate installed and configured
- HTTPS redirect enabled

### 3. Database Setup
- MySQL database created
- Database user with appropriate permissions
- Database accessible from application server

## Production Deployment Steps

### Step 1: Server Preparation

1. **Update system packages**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install required packages**
   ```bash
   sudo apt install python3 python3-pip python3-venv mysql-client -y
   ```

3. **Create application directory**
   ```bash
   sudo mkdir -p /var/www/epv
   sudo chown $USER:$USER /var/www/epv
   ```

### Step 2: Application Deployment

1. **Clone repository**
   ```bash
   cd /var/www/epv
   git clone <your-repository-url> .
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with production values
   nano .env
   ```

### Step 3: Database Configuration

1. **Create production database**
   ```sql
   CREATE DATABASE epv_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'epv_user'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON epv_production.* TO 'epv_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. **Update .env with database credentials**
   ```env
   DB_HOST=localhost
   DB_USER=epv_user
   DB_PASSWORD=secure_password
   DB_NAME=epv_production
   ```

3. **Initialize database**
   ```bash
   python app.py
   # Database tables will be created automatically
   ```

### Step 4: Production Environment Configuration

1. **Update .env for production**
   ```env
   FLASK_ENV=production
   OAUTHLIB_INSECURE_TRANSPORT=0
   FLASK_SECRET_KEY=your-very-secure-production-key
   ```

2. **Set file permissions**
   ```bash
   chmod 755 /var/www/epv
   chmod 644 /var/www/epv/*.py
   chmod 600 /var/www/epv/.env
   ```

3. **Create upload directories**
   ```bash
   mkdir -p uploads pdf_uploads
   chmod 755 uploads pdf_uploads
   ```

### Step 5: Web Server Configuration

#### For cPanel/Shared Hosting

1. **Upload files via File Manager or FTP**
   - Upload all files except: venv/, __pycache__/, uploads/, .git/

2. **Install Python packages**
   ```bash
   pip install --user -r requirements.txt
   ```

3. **Configure Python app in cPanel**
   - Application Root: `/EPV`
   - Application URL: `/`
   - Application Startup File: `app.py`
   - Application Entry Point: `application`

4. **passenger_wsgi.py configuration**
   ```python
   import os
   import sys
   
   # Add the application directory to the Python path
   sys.path.insert(0, os.path.dirname(__file__))
   
   # Import the Flask application
   from app import application
   
   # Make sure the application runs on the correct port
   if __name__ == "__main__":
       application.run()
   ```

#### For VPS/Dedicated Server with Apache

1. **Install mod_wsgi**
   ```bash
   sudo apt install libapache2-mod-wsgi-py3
   ```

2. **Create Apache virtual host**
   ```apache
   <VirtualHost *:443>
       ServerName yourdomain.com
       DocumentRoot /var/www/epv
       
       WSGIDaemonProcess epv python-path=/var/www/epv python-home=/var/www/epv/venv
       WSGIProcessGroup epv
       WSGIScriptAlias / /var/www/epv/passenger_wsgi.py
       
       <Directory /var/www/epv>
           WSGIApplicationGroup %{GLOBAL}
           Require all granted
       </Directory>
       
       # SSL Configuration
       SSLEngine on
       SSLCertificateFile /path/to/certificate.crt
       SSLCertificateKeyFile /path/to/private.key
   </VirtualHost>
   ```

### Step 6: Google OAuth Configuration

1. **Update Google Cloud Console**
   - Add production domain to authorized origins
   - Add production callback URL: `https://yourdomain.com/login/google/authorized`

2. **Test OAuth flow**
   - Visit your production site
   - Test login with Google account
   - Verify user data is stored correctly

### Step 7: Email Configuration

1. **Configure SMTP settings**
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-production-email@domain.com
   SMTP_PASSWORD=your-app-password
   ```

2. **Test email functionality**
   - Submit test expense
   - Verify approval emails are sent
   - Test rejection notifications

### Step 8: Security Hardening

1. **File permissions**
   ```bash
   find /var/www/epv -type f -exec chmod 644 {} \;
   find /var/www/epv -type d -exec chmod 755 {} \;
   chmod 600 /var/www/epv/.env
   ```

2. **Hide sensitive files**
   ```apache
   <Files ".env">
       Require all denied
   </Files>
   
   <Files "*.py">
       Require all denied
   </Files>
   ```

3. **Enable security headers**
   ```apache
   Header always set X-Content-Type-Options nosniff
   Header always set X-Frame-Options DENY
   Header always set X-XSS-Protection "1; mode=block"
   Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
   ```

## Post-Deployment Verification

### 1. Functionality Testing
- [ ] User registration and login
- [ ] Expense submission
- [ ] Manager approval emails
- [ ] Finance dashboard access
- [ ] PDF generation
- [ ] File uploads
- [ ] Email notifications

### 2. Performance Testing
- [ ] Page load times
- [ ] Database query performance
- [ ] File upload speeds
- [ ] Concurrent user handling

### 3. Security Testing
- [ ] HTTPS enforcement
- [ ] Session security
- [ ] File upload restrictions
- [ ] SQL injection protection
- [ ] XSS protection

## Monitoring and Maintenance

### 1. Log Monitoring
```bash
# Application logs
tail -f /var/log/apache2/error.log

# Database logs
tail -f /var/log/mysql/error.log
```

### 2. Backup Strategy
- **Database**: Daily automated backups
- **Files**: Weekly backup of uploads directory
- **Code**: Version control with Git

### 3. Update Process
1. Test updates in staging environment
2. Create backup before deployment
3. Deploy during maintenance window
4. Verify functionality post-deployment

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check database credentials in .env
   - Verify database server is running
   - Check firewall settings

2. **Google OAuth Errors**
   - Verify redirect URLs in Google Console
   - Check client ID and secret
   - Ensure HTTPS is properly configured

3. **Email Delivery Issues**
   - Verify SMTP credentials
   - Check spam folders
   - Test with different email providers

4. **File Upload Problems**
   - Check directory permissions
   - Verify disk space
   - Check file size limits

### Support Contacts
- **Technical Issues**: Create GitHub issue
- **Server Issues**: Contact hosting provider
- **Database Issues**: Contact database administrator

## Rollback Procedure

In case of deployment issues:

1. **Immediate rollback**
   ```bash
   git checkout previous-stable-tag
   sudo systemctl restart apache2
   ```

2. **Database rollback**
   ```bash
   mysql -u epv_user -p epv_production < backup_file.sql
   ```

3. **Verify rollback**
   - Test critical functionality
   - Check error logs
   - Notify users if necessary

# Production Deployment Guide

## Overview
This guide will help you deploy the EPV (Expense Portal) application to your production server.

## Pre-Deployment Checklist

### 1. Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services > Credentials**
3. Edit your OAuth 2.0 Client ID
4. Add your production domain to **Authorized redirect URIs**:
   ```
   https://yourdomain.com/login/google/authorized
   ```
5. Save the changes

### 2. Server Requirements
- Ubuntu 20.04+ (or similar Linux distribution)
- Python 3.8+
- MySQL 8.0+
- Nginx
- SSL Certificate (Let's Encrypt recommended)

## Step-by-Step Deployment

### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3 python3-pip python3-venv mysql-server nginx certbot python3-certbot-nginx -y

# Create application directory
sudo mkdir -p /var/www/epv-app
sudo chown $USER:$USER /var/www/epv-app
```

### 2. Database Setup
```bash
# Secure MySQL installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p
```

```sql
CREATE DATABASE AFDW;
CREATE USER 'epv_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON AFDW.* TO 'epv_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Application Deployment
```bash
# Navigate to application directory
cd /var/www/epv-app

# Upload your application files (via git, scp, or other method)
# If using git:
git clone your-repository-url .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy production environment file
cp .env_production .env

# Edit the .env file with your production values
nano .env
```

### 4. Configure Environment Variables
Edit the `.env` file and update these critical values:

```bash
# Generate a secure secret key
python3 -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"

# Update database credentials
DB_HOST=localhost
DB_USER=epv_user
DB_PASSWORD=your_secure_password

# Update email settings
SMTP_USERNAME=your-production-email@domain.com
SMTP_PASSWORD=your-email-app-password
```

### 5. Test the Application
```bash
# Test database connection and initialize tables
source venv/bin/activate
python app.py

# The app should start and show "Database initialized successfully"
# Press Ctrl+C to stop
```

### 6. Create Systemd Service
```bash
sudo nano /etc/systemd/system/epv-app.service
```

```ini
[Unit]
Description=EPV Flask Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/epv-app
Environment="PATH=/var/www/epv-app/venv/bin"
ExecStart=/var/www/epv-app/venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Set permissions
sudo chown -R www-data:www-data /var/www/epv-app

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable epv-app
sudo systemctl start epv-app

# Check status
sudo systemctl status epv-app
```

### 7. Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/epv-app
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static {
        alias /var/www/epv-app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    client_max_body_size 20M;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/epv-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. SSL Certificate
```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### 9. Final Testing
1. Visit `https://yourdomain.com`
2. Should show the login page
3. Test Google OAuth login
4. Verify all features work correctly

## Monitoring and Maintenance

### View Application Logs
```bash
# Application logs
sudo journalctl -u epv-app -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Application
```bash
sudo systemctl restart epv-app
```

### Update Application
```bash
cd /var/www/epv-app
git pull origin main  # or your main branch
sudo systemctl restart epv-app
```

## Security Considerations
- Keep your server updated
- Use strong passwords for database and email
- Regularly backup your database
- Monitor application logs for suspicious activity
- Keep SSL certificates updated

## Troubleshooting
- Check application logs: `sudo journalctl -u epv-app -f`
- Check Nginx configuration: `sudo nginx -t`
- Verify database connection: Test with MySQL client
- Check file permissions: Ensure www-data owns application files

## Support
If you encounter issues during deployment, check the logs and ensure all configuration values are correct.

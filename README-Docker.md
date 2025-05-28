# EPV Application - Docker Deployment Guide

This guide will help you deploy the EPV (Expense Processing and Verification) application using Docker containers.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- Ports 5000, 3306, 6379, and 80 available

### 1. Clone and Setup
```bash
# Navigate to your EPV project directory
cd EPV

# Make deployment script executable
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

### 2. Configure Environment
Edit the `.env` file with your actual configuration:
```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

### 3. Access Application
- **Application**: http://localhost:5000
- **Health Check**: http://localhost:5000/health

## 📋 Configuration

### Environment Variables (.env file)
```env
# Database
DB_HOST=db
DB_USER=epv_user
DB_PASSWORD=EPV_SecurePass123!
DB_NAME=epv_database

# Email (Gmail SMTP)
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Security
SECRET_KEY=your-super-secret-key
```

## 🐳 Docker Services

### Application Stack
- **web**: Flask application (Python 3.10)
- **db**: MySQL 8.0 database
- **redis**: Redis for session storage
- **nginx**: Reverse proxy (optional)

### Volumes
- `mysql_data`: Persistent database storage
- `redis_data`: Redis data persistence
- `./logs`: Application logs
- `./uploads`: File uploads
- `./temp`: Temporary files

## 🛠️ Management Commands

### Deployment
```bash
# Deploy application
./deploy.sh deploy

# Stop application
./deploy.sh stop

# Restart application
./deploy.sh restart

# View logs
./deploy.sh logs

# Check status
./deploy.sh status

# Clean up
./deploy.sh clean
```

### Docker Compose Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f web

# Execute commands in container
docker-compose exec web bash

# Database access
docker-compose exec db mysql -u epv_user -p epv_database
```

## 📊 Monitoring and Logs

### Log Files
- `logs/epv_app.log`: General application logs
- `logs/epv_errors.log`: Error logs only
- `logs/epv_finance.log`: Finance operations
- `logs/epv_auth.log`: Authentication events
- `logs/gunicorn_access.log`: HTTP access logs
- `logs/gunicorn_error.log`: Server errors

### Health Monitoring
```bash
# Check application health
curl http://localhost:5000/health

# Monitor logs in real-time
docker-compose logs -f web

# Check container status
docker-compose ps
```

## 🔧 Production Deployment

### AWS EC2 Deployment
1. **Launch EC2 Instance**
   - Ubuntu 20.04 LTS
   - t3.medium or larger
   - Security groups: 22, 80, 443, 5000

2. **Install Docker**
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose
   sudo usermod -aG docker $USER
   ```

3. **Deploy Application**
   ```bash
   git clone your-repo
   cd EPV
   chmod +x deploy.sh
   ./deploy.sh
   ```

### SSL Configuration
1. **Get SSL Certificate**
   ```bash
   # Using Let's Encrypt
   sudo apt install certbot
   sudo certbot certonly --standalone -d your-domain.com
   ```

2. **Update Nginx Configuration**
   ```bash
   # Copy certificates to ssl directory
   sudo cp /etc/letsencrypt/live/your-domain.com/* ./ssl/
   
   # Update nginx.conf with SSL settings
   # Uncomment SSL lines in nginx.conf
   ```

### Environment-Specific Configurations

#### Development
```env
FLASK_ENV=development
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
```

#### Production
```env
FLASK_ENV=production
FLASK_DEBUG=False
LOG_LEVEL=INFO
SESSION_COOKIE_SECURE=True
```

## 🔒 Security Considerations

### Database Security
- Change default passwords
- Use strong passwords
- Limit database access
- Regular backups

### Application Security
- Use HTTPS in production
- Set secure session cookies
- Regular security updates
- Monitor logs for suspicious activity

### Network Security
- Use firewall rules
- Limit exposed ports
- Use VPN for database access
- Regular security audits

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check database status
docker-compose logs db

# Restart database
docker-compose restart db
```

#### Application Won't Start
```bash
# Check application logs
docker-compose logs web

# Check environment variables
docker-compose exec web env
```

#### Port Already in Use
```bash
# Find process using port
sudo lsof -i :5000

# Kill process or change port in docker-compose.yml
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h
```

## 📈 Scaling

### Horizontal Scaling
```yaml
# In docker-compose.yml
web:
  scale: 3  # Run 3 instances
```

### Load Balancing
- Use nginx upstream configuration
- Configure health checks
- Session affinity with Redis

## 🔄 Backup and Recovery

### Database Backup
```bash
# Create backup
docker-compose exec db mysqldump -u epv_user -p epv_database > backup.sql

# Restore backup
docker-compose exec -T db mysql -u epv_user -p epv_database < backup.sql
```

### Application Backup
```bash
# Backup uploads and logs
tar -czf epv-backup-$(date +%Y%m%d).tar.gz uploads/ logs/
```

## 📞 Support

For issues and questions:
1. Check logs: `./deploy.sh logs`
2. Check status: `./deploy.sh status`
3. Review this documentation
4. Contact system administrator

## 🔄 Updates

### Application Updates
```bash
# Pull latest code
git pull

# Rebuild and deploy
./deploy.sh deploy
```

### Security Updates
```bash
# Update base images
docker-compose pull

# Rebuild with latest images
docker-compose build --no-cache
```

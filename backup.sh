#!/bin/bash

# EPV Application Backup Script
# This script creates backups of the database, uploads, and configuration

set -e

# Configuration
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Database configuration
DB_CONTAINER="epv-mysql"
DB_USER="epv_user"
DB_PASSWORD="EPV_SecurePass123!"
DB_NAME="epv_database"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Create backup directory
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        print_status "Created backup directory: $BACKUP_DIR"
    fi
}

# Backup database
backup_database() {
    print_info "Backing up database..."
    
    local backup_file="$BACKUP_DIR/epv_database_$DATE.sql"
    
    if docker-compose exec -T db mysqldump -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" > "$backup_file"; then
        print_status "Database backup created: $backup_file"
        
        # Compress the backup
        gzip "$backup_file"
        print_status "Database backup compressed: $backup_file.gz"
        
        return 0
    else
        print_error "Database backup failed"
        return 1
    fi
}

# Backup uploads directory
backup_uploads() {
    print_info "Backing up uploads..."
    
    if [ -d "./uploads" ]; then
        local backup_file="$BACKUP_DIR/epv_uploads_$DATE.tar.gz"
        
        if tar -czf "$backup_file" uploads/; then
            print_status "Uploads backup created: $backup_file"
            return 0
        else
            print_error "Uploads backup failed"
            return 1
        fi
    else
        print_warning "Uploads directory not found"
        return 1
    fi
}

# Backup logs
backup_logs() {
    print_info "Backing up logs..."
    
    if [ -d "./logs" ]; then
        local backup_file="$BACKUP_DIR/epv_logs_$DATE.tar.gz"
        
        if tar -czf "$backup_file" logs/; then
            print_status "Logs backup created: $backup_file"
            return 0
        else
            print_error "Logs backup failed"
            return 1
        fi
    else
        print_warning "Logs directory not found"
        return 1
    fi
}

# Backup configuration files
backup_config() {
    print_info "Backing up configuration..."
    
    local backup_file="$BACKUP_DIR/epv_config_$DATE.tar.gz"
    local config_files=()
    
    # Add configuration files to backup
    [ -f ".env" ] && config_files+=(".env")
    [ -f "docker-compose.yml" ] && config_files+=("docker-compose.yml")
    [ -f "docker-compose.prod.yml" ] && config_files+=("docker-compose.prod.yml")
    [ -f "nginx.conf" ] && config_files+=("nginx.conf")
    [ -f "mysql.cnf" ] && config_files+=("mysql.cnf")
    [ -f "gunicorn.conf.py" ] && config_files+=("gunicorn.conf.py")
    
    if [ ${#config_files[@]} -gt 0 ]; then
        if tar -czf "$backup_file" "${config_files[@]}"; then
            print_status "Configuration backup created: $backup_file"
            return 0
        else
            print_error "Configuration backup failed"
            return 1
        fi
    else
        print_warning "No configuration files found to backup"
        return 1
    fi
}

# Clean old backups
cleanup_old_backups() {
    print_info "Cleaning up old backups..."
    
    if [ -d "$BACKUP_DIR" ]; then
        # Find and delete files older than retention period
        local deleted_count=$(find "$BACKUP_DIR" -name "epv_*" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
        
        if [ "$deleted_count" -gt 0 ]; then
            print_status "Deleted $deleted_count old backup files"
        else
            print_status "No old backup files to delete"
        fi
    fi
}

# Verify backup integrity
verify_backups() {
    print_info "Verifying backup integrity..."
    
    local failed_verifications=0
    
    # Check database backup
    local db_backup="$BACKUP_DIR/epv_database_$DATE.sql.gz"
    if [ -f "$db_backup" ]; then
        if gzip -t "$db_backup"; then
            print_status "Database backup integrity verified"
        else
            print_error "Database backup integrity check failed"
            failed_verifications=$((failed_verifications + 1))
        fi
    fi
    
    # Check uploads backup
    local uploads_backup="$BACKUP_DIR/epv_uploads_$DATE.tar.gz"
    if [ -f "$uploads_backup" ]; then
        if tar -tzf "$uploads_backup" > /dev/null; then
            print_status "Uploads backup integrity verified"
        else
            print_error "Uploads backup integrity check failed"
            failed_verifications=$((failed_verifications + 1))
        fi
    fi
    
    # Check logs backup
    local logs_backup="$BACKUP_DIR/epv_logs_$DATE.tar.gz"
    if [ -f "$logs_backup" ]; then
        if tar -tzf "$logs_backup" > /dev/null; then
            print_status "Logs backup integrity verified"
        else
            print_error "Logs backup integrity check failed"
            failed_verifications=$((failed_verifications + 1))
        fi
    fi
    
    # Check config backup
    local config_backup="$BACKUP_DIR/epv_config_$DATE.tar.gz"
    if [ -f "$config_backup" ]; then
        if tar -tzf "$config_backup" > /dev/null; then
            print_status "Configuration backup integrity verified"
        else
            print_error "Configuration backup integrity check failed"
            failed_verifications=$((failed_verifications + 1))
        fi
    fi
    
    return $failed_verifications
}

# List available backups
list_backups() {
    print_info "Available backups:"
    
    if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR)" ]; then
        echo ""
        echo "Database backups:"
        ls -lh "$BACKUP_DIR"/epv_database_*.sql.gz 2>/dev/null || echo "  No database backups found"
        
        echo ""
        echo "Uploads backups:"
        ls -lh "$BACKUP_DIR"/epv_uploads_*.tar.gz 2>/dev/null || echo "  No uploads backups found"
        
        echo ""
        echo "Logs backups:"
        ls -lh "$BACKUP_DIR"/epv_logs_*.tar.gz 2>/dev/null || echo "  No logs backups found"
        
        echo ""
        echo "Configuration backups:"
        ls -lh "$BACKUP_DIR"/epv_config_*.tar.gz 2>/dev/null || echo "  No configuration backups found"
        
        echo ""
        echo "Total backup size:"
        du -sh "$BACKUP_DIR" 2>/dev/null || echo "  Unable to calculate size"
    else
        print_warning "No backups found in $BACKUP_DIR"
    fi
}

# Restore database from backup
restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        print_error "Please specify a backup file to restore"
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi
    
    print_warning "This will overwrite the current database. Are you sure? (y/N)"
    read -r confirmation
    
    if [ "$confirmation" != "y" ] && [ "$confirmation" != "Y" ]; then
        print_info "Database restore cancelled"
        return 0
    fi
    
    print_info "Restoring database from: $backup_file"
    
    # Decompress and restore
    if zcat "$backup_file" | docker-compose exec -T db mysql -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME"; then
        print_status "Database restored successfully"
        return 0
    else
        print_error "Database restore failed"
        return 1
    fi
}

# Full backup
full_backup() {
    echo "🗄️  EPV Application Full Backup"
    echo "=============================="
    echo "Started: $(date)"
    echo ""
    
    create_backup_dir
    
    local failed_backups=0
    
    backup_database || failed_backups=$((failed_backups + 1))
    backup_uploads || failed_backups=$((failed_backups + 1))
    backup_logs || failed_backups=$((failed_backups + 1))
    backup_config || failed_backups=$((failed_backups + 1))
    
    echo ""
    print_info "Verifying backups..."
    verify_backups || print_warning "Some backup verifications failed"
    
    echo ""
    cleanup_old_backups
    
    echo ""
    echo "=============================="
    
    if [ "$failed_backups" -eq 0 ]; then
        print_status "Full backup completed successfully!"
    else
        print_warning "$failed_backups backup operations failed"
    fi
    
    echo "Completed: $(date)"
    echo ""
    
    list_backups
    
    return $failed_backups
}

# Handle script arguments
case "${1:-backup}" in
    "backup"|"full")
        full_backup
        ;;
    "database")
        create_backup_dir
        backup_database
        ;;
    "uploads")
        create_backup_dir
        backup_uploads
        ;;
    "logs")
        create_backup_dir
        backup_logs
        ;;
    "config")
        create_backup_dir
        backup_config
        ;;
    "list")
        list_backups
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "restore")
        restore_database "$2"
        ;;
    "verify")
        verify_backups
        ;;
    *)
        echo "Usage: $0 {backup|database|uploads|logs|config|list|cleanup|restore|verify}"
        echo ""
        echo "Commands:"
        echo "  backup     - Create full backup (default)"
        echo "  database   - Backup database only"
        echo "  uploads    - Backup uploads only"
        echo "  logs       - Backup logs only"
        echo "  config     - Backup configuration only"
        echo "  list       - List available backups"
        echo "  cleanup    - Remove old backups"
        echo "  restore    - Restore database from backup file"
        echo "  verify     - Verify backup integrity"
        echo ""
        echo "Examples:"
        echo "  $0 backup                                    # Full backup"
        echo "  $0 restore backups/epv_database_20231201.sql.gz  # Restore database"
        exit 1
        ;;
esac

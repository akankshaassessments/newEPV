#!/bin/bash

# EPV Application Monitoring Script
# This script monitors the health and performance of the EPV application

set -e

# Configuration
LOG_DIR="./logs"
ALERT_EMAIL="${ALERT_EMAIL:-admin@yourcompany.com}"
ERROR_THRESHOLD=10
DISK_THRESHOLD=80
MEMORY_THRESHOLD=80

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to print colored output
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

# Function to send alert (placeholder - implement with your preferred method)
send_alert() {
    local subject="$1"
    local message="$2"
    
    echo "ALERT: $subject" >> "$LOG_DIR/alerts.log"
    echo "$(date): $message" >> "$LOG_DIR/alerts.log"
    
    # Uncomment and configure for email alerts
    # echo "$message" | mail -s "$subject" "$ALERT_EMAIL"
    
    # Uncomment for Slack alerts
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"$subject: $message\"}" \
    #   YOUR_SLACK_WEBHOOK_URL
}

# Check application health
check_application_health() {
    print_info "Checking application health..."
    
    if curl -f -s http://localhost:5000/health > /dev/null; then
        print_status "Application is healthy"
        return 0
    else
        print_error "Application health check failed"
        send_alert "EPV Application Down" "Application health check failed at $(date)"
        return 1
    fi
}

# Check database connectivity
check_database() {
    print_info "Checking database connectivity..."
    
    if docker-compose exec -T db mysqladmin ping -h localhost -u epv_user -pEPV_SecurePass123! > /dev/null 2>&1; then
        print_status "Database is accessible"
        return 0
    else
        print_error "Database connection failed"
        send_alert "EPV Database Issue" "Database connection failed at $(date)"
        return 1
    fi
}

# Check Redis connectivity
check_redis() {
    print_info "Checking Redis connectivity..."
    
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_status "Redis is accessible"
        return 0
    else
        print_error "Redis connection failed"
        send_alert "EPV Redis Issue" "Redis connection failed at $(date)"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    print_info "Checking disk space..."
    
    local disk_usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt "$DISK_THRESHOLD" ]; then
        print_warning "Disk usage is at $disk_usage%"
        send_alert "EPV Disk Space Warning" "Disk usage is at $disk_usage% on $(date)"
        return 1
    else
        print_status "Disk usage is at $disk_usage%"
        return 0
    fi
}

# Check memory usage
check_memory() {
    print_info "Checking memory usage..."
    
    local memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    
    if [ "$memory_usage" -gt "$MEMORY_THRESHOLD" ]; then
        print_warning "Memory usage is at $memory_usage%"
        send_alert "EPV Memory Warning" "Memory usage is at $memory_usage% on $(date)"
        return 1
    else
        print_status "Memory usage is at $memory_usage%"
        return 0
    fi
}

# Check for recent errors in logs
check_error_logs() {
    print_info "Checking for recent errors..."
    
    if [ ! -f "$LOG_DIR/epv_errors.log" ]; then
        print_status "No error log file found"
        return 0
    fi
    
    # Count errors in the last hour
    local error_count=$(grep "$(date '+%Y-%m-%d %H')" "$LOG_DIR/epv_errors.log" 2>/dev/null | wc -l)
    
    if [ "$error_count" -gt "$ERROR_THRESHOLD" ]; then
        print_warning "High error count: $error_count errors in the last hour"
        send_alert "EPV High Error Rate" "$error_count errors detected in the last hour"
        return 1
    else
        print_status "Error count is normal: $error_count errors in the last hour"
        return 0
    fi
}

# Check container status
check_containers() {
    print_info "Checking container status..."
    
    local containers=$(docker-compose ps -q)
    local failed_containers=0
    
    for container in $containers; do
        local status=$(docker inspect --format='{{.State.Status}}' "$container")
        local name=$(docker inspect --format='{{.Name}}' "$container" | sed 's/\///')
        
        if [ "$status" != "running" ]; then
            print_error "Container $name is $status"
            failed_containers=$((failed_containers + 1))
        else
            print_status "Container $name is running"
        fi
    done
    
    if [ "$failed_containers" -gt 0 ]; then
        send_alert "EPV Container Issues" "$failed_containers containers are not running"
        return 1
    fi
    
    return 0
}

# Check log file sizes
check_log_sizes() {
    print_info "Checking log file sizes..."
    
    if [ ! -d "$LOG_DIR" ]; then
        print_warning "Log directory not found"
        return 1
    fi
    
    local large_logs=0
    
    for log_file in "$LOG_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            local size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo 0)
            local size_mb=$((size / 1024 / 1024))
            
            if [ "$size_mb" -gt 100 ]; then
                print_warning "Large log file: $(basename "$log_file") is ${size_mb}MB"
                large_logs=$((large_logs + 1))
            fi
        fi
    done
    
    if [ "$large_logs" -eq 0 ]; then
        print_status "Log file sizes are normal"
    fi
    
    return 0
}

# Generate monitoring report
generate_report() {
    local report_file="$LOG_DIR/monitoring_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "EPV Application Monitoring Report"
        echo "Generated: $(date)"
        echo "================================="
        echo ""
        
        echo "System Information:"
        echo "- Hostname: $(hostname)"
        echo "- Uptime: $(uptime)"
        echo "- Load Average: $(uptime | awk -F'load average:' '{print $2}')"
        echo ""
        
        echo "Container Status:"
        docker-compose ps
        echo ""
        
        echo "Resource Usage:"
        echo "- Memory: $(free -h | grep Mem)"
        echo "- Disk: $(df -h . | tail -1)"
        echo ""
        
        echo "Recent Errors (last 24 hours):"
        if [ -f "$LOG_DIR/epv_errors.log" ]; then
            grep "$(date -d '1 day ago' '+%Y-%m-%d')" "$LOG_DIR/epv_errors.log" 2>/dev/null | tail -10 || echo "No recent errors found"
        else
            echo "No error log file found"
        fi
        
    } > "$report_file"
    
    print_status "Monitoring report generated: $report_file"
}

# Main monitoring function
run_monitoring() {
    echo "🔍 EPV Application Monitoring"
    echo "============================="
    echo "Started: $(date)"
    echo ""
    
    local issues=0
    
    # Run all checks
    check_application_health || issues=$((issues + 1))
    check_database || issues=$((issues + 1))
    check_redis || issues=$((issues + 1))
    check_containers || issues=$((issues + 1))
    check_disk_space || issues=$((issues + 1))
    check_memory || issues=$((issues + 1))
    check_error_logs || issues=$((issues + 1))
    check_log_sizes || issues=$((issues + 1))
    
    echo ""
    echo "============================="
    
    if [ "$issues" -eq 0 ]; then
        print_status "All checks passed! System is healthy."
    else
        print_warning "$issues issues detected. Check logs for details."
    fi
    
    echo "Completed: $(date)"
    
    # Generate report if requested
    if [ "${1:-}" = "--report" ]; then
        generate_report
    fi
    
    return $issues
}

# Handle script arguments
case "${1:-monitor}" in
    "monitor")
        run_monitoring
        ;;
    "report")
        run_monitoring --report
        ;;
    "health")
        check_application_health
        ;;
    "database")
        check_database
        ;;
    "redis")
        check_redis
        ;;
    "containers")
        check_containers
        ;;
    "logs")
        check_error_logs
        ;;
    *)
        echo "Usage: $0 {monitor|report|health|database|redis|containers|logs}"
        echo ""
        echo "Commands:"
        echo "  monitor    - Run all monitoring checks (default)"
        echo "  report     - Run monitoring and generate report"
        echo "  health     - Check application health only"
        echo "  database   - Check database connectivity only"
        echo "  redis      - Check Redis connectivity only"
        echo "  containers - Check container status only"
        echo "  logs       - Check error logs only"
        exit 1
        ;;
esac

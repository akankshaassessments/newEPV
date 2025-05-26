# EPV Application Error Handling Guide

This document provides a comprehensive guide to common errors that may occur in the EPV (Expense Processing Voucher) application and how to handle them.

## Table of Contents
1. [Database Errors](#database-errors)
2. [Authentication Errors](#authentication-errors)
3. [File Processing Errors](#file-processing-errors)
4. [Email Errors](#email-errors)
5. [Environment Configuration Errors](#environment-configuration-errors)
6. [API Integration Errors](#api-integration-errors)
7. [Dependency Errors](#dependency-errors)
8. [Server Deployment Errors](#server-deployment-errors)
9. [Performance Issues](#performance-issues)
10. [Security Concerns](#security-concerns)

## Database Errors

### Connection Issues
- **Error**: `OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server on 'localhost'")`
  - **Cause**: MySQL server is not running or connection parameters are incorrect
  - **Solution**: Verify MySQL is running, check host, port, and credentials in .env file

- **Error**: `OperationalError: (pymysql.err.OperationalError) (1045, "Access denied for user 'username'@'localhost'")`
  - **Cause**: Incorrect database credentials
  - **Solution**: Verify DB_USER and DB_PASSWORD in .env file

- **Error**: `UnicodeEncodeError: 'latin-1' codec can't encode characters in position...`
  - **Cause**: Special characters in database password not properly encoded
  - **Solution**: Ensure password is URL-encoded in the connection string

### Query Errors
- **Error**: `ProgrammingError: (pymysql.err.ProgrammingError) (1146, "Table 'webappor_AFDW.non_existent_table' doesn't exist")`
  - **Cause**: Referencing a table that doesn't exist
  - **Solution**: Check table names and run database migrations

- **Error**: `IntegrityError: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'value' for key 'unique_constraint'")`
  - **Cause**: Attempting to insert a duplicate value in a unique column
  - **Solution**: Check for existing records before insertion

### Migration Errors
- **Error**: `alembic.util.exc.CommandError: Can't locate revision identified by 'revision_id'`
  - **Cause**: Missing migration files or incorrect database state
  - **Solution**: Reset migrations or manually fix the alembic_version table

## Authentication Errors

### Google OAuth Errors
- **Error**: `OAuth error from google! invalid_grant`
  - **Cause**: Expired or revoked refresh token
  - **Solution**: Clear user's session and have them log in again

- **Error**: `OAuth error from google! redirect_uri_mismatch`
  - **Cause**: Redirect URI doesn't match those configured in Google Cloud Console
  - **Solution**: Add the URI to the allowed redirect URIs in Google Cloud Console

- **Error**: `OAuth error from google! invalid_client`
  - **Cause**: Incorrect client ID or client secret
  - **Solution**: Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file

### Session Errors
- **Error**: `RuntimeError: The session is unavailable because no secret key was set.`
  - **Cause**: Flask app secret key not set
  - **Solution**: Set FLASK_SECRET_KEY in .env file

- **Error**: `KeyError: 'user_info'` or `KeyError: 'email'`
  - **Cause**: Accessing session data that doesn't exist
  - **Solution**: Check if user is authenticated before accessing session data

## File Processing Errors

### PDF Generation Errors
- **Error**: `OSError: [Errno 2] No such file or directory: 'wkhtmltopdf'`
  - **Cause**: Missing wkhtmltopdf binary for pdfkit
  - **Solution**: Install wkhtmltopdf on the server

- **Error**: `IOError: [Errno 13] Permission denied: '/path/to/file.pdf'`
  - **Cause**: Insufficient permissions to write to the file
  - **Solution**: Check file permissions and ownership

### File Upload Errors
- **Error**: `RequestEntityTooLarge: 413 Request Entity Too Large`
  - **Cause**: Uploaded file exceeds size limit
  - **Solution**: Increase upload limit in server configuration or compress files

- **Error**: `OSError: [Errno 28] No space left on device`
  - **Cause**: Server disk is full
  - **Solution**: Free up disk space or increase storage capacity

### Google Drive Errors
- **Error**: `googleapiclient.errors.HttpError: <HttpError 403 when requesting ... returned "Insufficient Permission">`
  - **Cause**: Insufficient permissions to access or modify Google Drive files
  - **Solution**: Check OAuth scopes and file permissions

- **Error**: `googleapiclient.errors.HttpError: <HttpError 404 when requesting ... returned "File not found">`
  - **Cause**: Attempting to access a deleted or non-existent file
  - **Solution**: Verify file IDs and handle missing files gracefully

## Email Errors

### SMTP Errors
- **Error**: `SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted')`
  - **Cause**: Incorrect SMTP credentials
  - **Solution**: Verify email username and password in .env file

- **Error**: `SMTPConnectError: (421, b'4.7.0 Temporary System Problem')`
  - **Cause**: SMTP server is temporarily unavailable
  - **Solution**: Implement retry logic with exponential backoff

- **Error**: `SMTPRecipientsRefused: {'recipient@example.com': (550, b'5.1.1 User unknown')`
  - **Cause**: Invalid recipient email address
  - **Solution**: Validate email addresses before sending

### Rate Limiting
- **Error**: `SMTPDataError: (450, b'4.4.2 Mailbox busy')`
  - **Cause**: Sending too many emails too quickly
  - **Solution**: Implement rate limiting and queuing for emails

## Environment Configuration Errors

### Missing Variables
- **Error**: `KeyError: 'DB_HOST'` or similar
  - **Cause**: Required environment variable is missing
  - **Solution**: Ensure all required variables are in .env file

### Format Errors
- **Error**: `ValueError: invalid literal for int() with base 10: 'not_a_number'`
  - **Cause**: Environment variable has incorrect format
  - **Solution**: Ensure variables have correct format (e.g., PORT should be a number)

## API Integration Errors

### Rate Limiting
- **Error**: `googleapiclient.errors.HttpError: <HttpError 429 when requesting ... returned "Rate Limit Exceeded">`
  - **Cause**: Too many requests to Google API
  - **Solution**: Implement exponential backoff and request batching

### Authentication Errors
- **Error**: `googleapiclient.errors.HttpError: <HttpError 401 when requesting ... returned "Invalid Credentials">`
  - **Cause**: Expired or invalid API credentials
  - **Solution**: Refresh tokens or re-authenticate

## Dependency Errors

### Version Conflicts
- **Error**: `ImportError: cannot import name 'X' from 'Y'`
  - **Cause**: Incompatible package versions
  - **Solution**: Pin dependencies to specific versions in requirements.txt

### Missing Dependencies
- **Error**: `ModuleNotFoundError: No module named 'package_name'`
  - **Cause**: Required package is not installed
  - **Solution**: Install missing package with pip

## Server Deployment Errors

### WSGI Errors
- **Error**: `ImportError: No module named 'app'`
  - **Cause**: Incorrect WSGI configuration
  - **Solution**: Verify app name and path in passenger_wsgi.py

### Port Binding Errors
- **Error**: `OSError: [Errno 98] Address already in use`
  - **Cause**: Port 5000 is already in use
  - **Solution**: Stop other processes using port 5000 or use a different port

## Performance Issues

### Slow Database Queries
- **Symptom**: Pages load very slowly
  - **Cause**: Inefficient database queries
  - **Solution**: Add indexes, optimize queries, implement caching

### Memory Leaks
- **Symptom**: Server memory usage grows over time
  - **Cause**: Resources not being properly released
  - **Solution**: Profile application and fix memory leaks

## Security Concerns

### CSRF Vulnerabilities
- **Risk**: Cross-Site Request Forgery attacks
  - **Protection**: Ensure CSRF tokens are used in all forms

### SQL Injection
- **Risk**: Malicious SQL code execution
  - **Protection**: Use SQLAlchemy's parameterized queries, never string concatenation

### XSS Vulnerabilities
- **Risk**: Cross-Site Scripting attacks
  - **Protection**: Escape user input, use Content Security Policy

## Debugging Tips

1. **Enable Debug Mode**: Set `FLASK_DEBUG=1` for detailed error messages (development only)
2. **Check Logs**: Review application logs for error details
3. **Use Try-Except**: Wrap critical operations in try-except blocks with specific error handling
4. **Implement Logging**: Use Python's logging module to record errors and warnings
5. **Test in Isolation**: Test components individually to isolate issues

## Preventive Measures

1. **Input Validation**: Validate all user inputs before processing
2. **Error Monitoring**: Implement Sentry or similar error tracking
3. **Automated Testing**: Create unit and integration tests
4. **Graceful Degradation**: Design the application to work even when some components fail
5. **Regular Backups**: Maintain regular database backups

## Contact

For critical issues, contact the development team at:
- Email: nikhil.aher@akanksha.org

-- Manual SQL script to clean up local database
-- Run this in your MySQL client (phpMyAdmin, MySQL Workbench, or command line)

-- Drop User and OAuth tables from local database
-- These are no longer needed since we use EmployeeDetails for Flask-Login

-- Disable foreign key checks temporarily
SET FOREIGN_KEY_CHECKS = 0;

-- Drop oauth table first (has foreign key to users)
DROP TABLE IF EXISTS oauth;

-- Drop users table
DROP TABLE IF EXISTS users;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Verify tables are dropped
SHOW TABLES LIKE 'users';
SHOW TABLES LIKE 'oauth';

-- If the above queries return empty results, the cleanup was successful
-- Your local database now matches the server structure

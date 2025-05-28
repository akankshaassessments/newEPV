-- EPV Database Initialization Script
-- This script will be run when the MySQL container starts for the first time

-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS epv_database CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE epv_database;

-- Grant privileges to the epv_user
GRANT ALL PRIVILEGES ON epv_database.* TO 'epv_user'@'%';
FLUSH PRIVILEGES;

-- Create a sample admin user (you should change this in production)
-- This is just for initial setup - the application will create proper tables
INSERT IGNORE INTO mysql.user (Host, User, Password, ssl_cipher, x509_issuer, x509_subject) 
VALUES ('%', 'epv_admin', PASSWORD('EPV_Admin_Pass123!'), '', '', '');

GRANT ALL PRIVILEGES ON epv_database.* TO 'epv_admin'@'%';
FLUSH PRIVILEGES;

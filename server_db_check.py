#!/usr/bin/env python3
"""
Script to run ON THE SERVER to check database structure
Upload this file to your server and run it there
"""
import pymysql
import sys
import os

# Database connection details for localhost (when running on server)
DB_CONFIG = {
    'host': '190.92.174.212',  # Use localhost when running on server
    'port': 3306,
    'user': 'webappor_IT',
    'password': 'Motoming@123',
    'database': 'webappor_AFDW',
    'charset': 'utf8mb4'
}

def connect_to_database():
    """Connect to the MySQL database"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print(f"✅ Successfully connected to database: {DB_CONFIG['database']}")
        return connection
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None

def show_all_tables(connection):
    """Show all tables in the database"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print(f"\n📋 All tables in database '{DB_CONFIG['database']}':")
            print("=" * 50)
            
            if tables:
                for i, table in enumerate(tables, 1):
                    print(f"{i:2d}. {table[0]}")
            else:
                print("No tables found in the database.")
                
            return [table[0] for table in tables]
    except Exception as e:
        print(f"❌ Error fetching tables: {e}")
        return []

def check_epv_table_columns(connection):
    """Check EPV table columns and generate ALTER statements for missing ones"""
    try:
        with connection.cursor() as cursor:
            # Check if EPV table exists
            cursor.execute("SHOW TABLES LIKE 'epv'")
            if not cursor.fetchone():
                print("❌ EPV table does not exist!")
                return []
            
            cursor.execute("DESCRIBE epv")
            columns = cursor.fetchall()
            
            existing_columns = [col[0] for col in columns]
            
            # Expected columns in EPV table based on your model
            expected_columns = {
                'id': 'INT AUTO_INCREMENT PRIMARY KEY',
                'epv_id': 'VARCHAR(30) UNIQUE NOT NULL',
                'email_id': 'VARCHAR(100) NOT NULL',
                'employee_name': 'VARCHAR(100) NOT NULL',
                'employee_id': 'VARCHAR(50) NOT NULL',
                'from_date': 'DATE NOT NULL',
                'to_date': 'DATE NOT NULL',
                'payment_to': 'VARCHAR(100) NOT NULL',
                'acknowledgement': 'VARCHAR(255)',
                'document_status': "VARCHAR(50) DEFAULT 'complete'",
                'requested_documents': 'TEXT',
                'submission_date': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                'academic_year': 'VARCHAR(20)',
                'cost_center_id': 'INT',
                'cost_center_name': 'VARCHAR(100) NOT NULL',
                'city': 'VARCHAR(50)',
                'file_url': 'VARCHAR(255)',
                'drive_file_id': 'VARCHAR(100)',
                'total_amount': 'FLOAT NOT NULL',
                'amount_in_words': 'VARCHAR(255)',
                'invoice_type': "VARCHAR(20) DEFAULT 'standard'",
                'master_invoice_id': 'INT',
                'split_status': 'VARCHAR(20)',
                'approved_amount': 'FLOAT DEFAULT 0.0',
                'rejected_amount': 'FLOAT DEFAULT 0.0',
                'pending_amount': 'FLOAT DEFAULT 0.0',
                'status': "VARCHAR(20) DEFAULT 'submitted'",
                'finance_status': 'VARCHAR(20)',
                'being_processed_by': 'INT',
                'processing_started_at': 'DATETIME',
                'approver_emails': 'TEXT',
                'approved_by': 'VARCHAR(100)',
                'approved_on': 'DATETIME',
                'rejected_by': 'VARCHAR(100)',
                'rejected_on': 'DATETIME',
                'rejection_reason': 'TEXT'
            }
            
            print(f"\n🔍 EPV Table Column Analysis:")
            print("=" * 60)
            
            missing_columns = []
            for col, definition in expected_columns.items():
                if col in existing_columns:
                    print(f"✅ {col}")
                else:
                    missing_columns.append((col, definition))
                    print(f"❌ {col} - MISSING")
            
            if missing_columns:
                print(f"\n🔧 SQL Commands to Fix Missing Columns:")
                print("=" * 50)
                print("-- Copy and paste these commands into phpMyAdmin or MySQL console:")
                print()
                
                for col, definition in missing_columns:
                    print(f"ALTER TABLE epv ADD COLUMN {col} {definition};")
                
                print()
                print("-- After adding columns, you may also need to add foreign key constraints:")
                if any(col[0] == 'cost_center_id' for col in missing_columns):
                    print("-- ALTER TABLE epv ADD CONSTRAINT fk_epv_cost_center FOREIGN KEY (cost_center_id) REFERENCES costcenter(id);")
                if any(col[0] == 'being_processed_by' for col in missing_columns):
                    print("-- ALTER TABLE epv ADD CONSTRAINT fk_epv_processor FOREIGN KEY (being_processed_by) REFERENCES employee_details(id);")
                if any(col[0] == 'master_invoice_id' for col in missing_columns):
                    print("-- ALTER TABLE epv ADD CONSTRAINT fk_epv_master FOREIGN KEY (master_invoice_id) REFERENCES epv(id);")
            else:
                print("✅ All EPV table columns are present!")
            
            return missing_columns
            
    except Exception as e:
        print(f"❌ Error checking EPV table: {e}")
        return []

def check_other_tables(connection):
    """Check for other required tables"""
    required_tables = {
        'costcenter': '''
CREATE TABLE costcenter (
    id INT AUTO_INCREMENT PRIMARY KEY,
    costcenter VARCHAR(100) NOT NULL,
    approver_email VARCHAR(100),
    city VARCHAR(50),
    drive_id VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE
);''',
        'employee_details': '''
CREATE TABLE employee_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    employee_id VARCHAR(50),
    manager VARCHAR(100),
    manager_name VARCHAR(100),
    name VARCHAR(100),
    role VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE
);''',
        'epv_item': '''
CREATE TABLE epv_item (
    id INT AUTO_INCREMENT PRIMARY KEY,
    epv_id INT NOT NULL,
    expense_invoice_date DATE NOT NULL,
    expense_head VARCHAR(100) NOT NULL,
    description TEXT,
    gst FLOAT DEFAULT 0.0,
    amount FLOAT NOT NULL,
    receipt_filename VARCHAR(255),
    receipt_path VARCHAR(255),
    receipt_drive_id VARCHAR(100),
    split_invoice BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (epv_id) REFERENCES epv(id)
);''',
        'epv_approval': '''
CREATE TABLE epv_approval (
    id INT AUTO_INCREMENT PRIMARY KEY,
    epv_id INT NOT NULL,
    allocation_id INT,
    approver_email VARCHAR(100) NOT NULL,
    approver_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    action_date DATETIME,
    comments TEXT,
    token VARCHAR(100) UNIQUE,
    FOREIGN KEY (epv_id) REFERENCES epv(id)
);''',
        'epv_allocation': '''
CREATE TABLE epv_allocation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    epv_id INT NOT NULL,
    cost_center_id INT NOT NULL,
    cost_center_name VARCHAR(100) NOT NULL,
    allocated_amount FLOAT NOT NULL,
    description TEXT,
    expense_head VARCHAR(100),
    approver_email VARCHAR(100) NOT NULL,
    approver_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    action_date DATETIME,
    rejection_reason TEXT,
    token VARCHAR(100) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (epv_id) REFERENCES epv(id),
    FOREIGN KEY (cost_center_id) REFERENCES costcenter(id)
);'''
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            existing_tables = [table[0] for table in cursor.fetchall()]
            
            print(f"\n📋 Required Tables Check:")
            print("=" * 40)
            
            missing_tables = []
            for table_name, create_sql in required_tables.items():
                if table_name in existing_tables:
                    print(f"✅ {table_name}")
                else:
                    print(f"❌ {table_name} - MISSING")
                    missing_tables.append((table_name, create_sql))
            
            if missing_tables:
                print(f"\n🔧 SQL Commands to Create Missing Tables:")
                print("=" * 50)
                for table_name, create_sql in missing_tables:
                    print(f"-- Create {table_name} table:")
                    print(create_sql)
                    print()
            
            return missing_tables
            
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return []

def main():
    """Main function"""
    print("🔗 Checking Production Database Structure...")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   User: {DB_CONFIG['user']}")
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        print("\n💡 If connection failed, make sure you're running this script ON THE SERVER")
        print("   Upload this file to your server and run: python3 server_db_check.py")
        sys.exit(1)
    
    try:
        # Show all tables
        all_tables = show_all_tables(connection)
        
        # Check EPV table columns
        missing_epv_columns = check_epv_table_columns(connection)
        
        # Check other required tables
        missing_tables = check_other_tables(connection)
        
        print(f"\n📊 Summary:")
        print("=" * 30)
        if missing_epv_columns:
            print(f"❌ EPV table missing {len(missing_epv_columns)} columns")
        else:
            print("✅ EPV table structure is complete")
            
        if missing_tables:
            print(f"❌ Missing {len(missing_tables)} required tables")
        else:
            print("✅ All required tables exist")
        
        if missing_epv_columns or missing_tables:
            print(f"\n⚠️  Action Required: Run the SQL commands shown above to fix the database structure")
        else:
            print(f"\n🎉 Database structure is complete!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    
    finally:
        connection.close()
        print(f"\n🔌 Database connection closed.")

if __name__ == "__main__":
    main()

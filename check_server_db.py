#!/usr/bin/env python3
"""
Script to connect to the production database and check table structure
"""
import pymysql
import sys

# Database connection details
DB_CONFIG = {
    'host': '190.92.174.212',
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

def show_table_structure(connection, table_name):
    """Show the structure of a specific table"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            
            print(f"\n🔍 Structure of table '{table_name}':")
            print("-" * 80)
            print(f"{'Field':<25} {'Type':<20} {'Null':<5} {'Key':<5} {'Default':<10} {'Extra'}")
            print("-" * 80)
            
            for column in columns:
                field, type_info, null, key, default, extra = column
                default_str = str(default) if default is not None else 'NULL'
                print(f"{field:<25} {type_info:<20} {null:<5} {key:<5} {default_str:<10} {extra}")
                
    except Exception as e:
        print(f"❌ Error fetching table structure for {table_name}: {e}")

def check_app_related_tables(connection, all_tables):
    """Check which tables are related to our EPV application"""
    
    # Expected tables for our EPV application
    expected_tables = [
        'costcenter',
        'employee_details', 
        'city_assignment',
        'settings_finance',
        'expense_head',
        'epv',
        'epv_item',
        'epv_approval',
        'epv_allocation',
        'finance_entry',
        'supplementary_document',
        'users',
        'oauth'
    ]
    
    print(f"\n🎯 EPV Application Tables Analysis:")
    print("=" * 60)
    
    found_tables = []
    missing_tables = []
    
    for table in expected_tables:
        if table in all_tables:
            found_tables.append(table)
            print(f"✅ {table} - EXISTS")
        else:
            missing_tables.append(table)
            print(f"❌ {table} - MISSING")
    
    print(f"\n📊 Summary:")
    print(f"   Found: {len(found_tables)}/{len(expected_tables)} tables")
    print(f"   Missing: {len(missing_tables)} tables")
    
    if missing_tables:
        print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
    
    return found_tables, missing_tables

def check_epv_table_columns(connection):
    """Specifically check the EPV table for missing columns"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("DESCRIBE epv")
            columns = cursor.fetchall()
            
            existing_columns = [col[0] for col in columns]
            
            # Expected columns in EPV table
            expected_columns = [
                'id', 'epv_id', 'email_id', 'employee_name', 'employee_id',
                'from_date', 'to_date', 'payment_to', 'acknowledgement',
                'document_status', 'requested_documents', 'submission_date',
                'academic_year', 'cost_center_id', 'cost_center_name', 'city',
                'file_url', 'drive_file_id', 'total_amount', 'amount_in_words',
                'invoice_type', 'master_invoice_id', 'split_status',
                'approved_amount', 'rejected_amount', 'pending_amount',
                'status', 'finance_status', 'being_processed_by',
                'processing_started_at', 'approver_emails', 'approved_by',
                'approved_on', 'rejected_by', 'rejected_on', 'rejection_reason'
            ]
            
            print(f"\n🔍 EPV Table Column Analysis:")
            print("=" * 50)
            
            missing_columns = []
            for col in expected_columns:
                if col in existing_columns:
                    print(f"✅ {col}")
                else:
                    missing_columns.append(col)
                    print(f"❌ {col} - MISSING")
            
            if missing_columns:
                print(f"\n⚠️  Missing columns in EPV table:")
                for col in missing_columns:
                    print(f"   - {col}")
                    
                print(f"\n🔧 SQL commands to add missing columns:")
                print("-" * 40)
                
                column_definitions = {
                    'document_status': "VARCHAR(50) DEFAULT 'complete'",
                    'requested_documents': "TEXT NULL",
                    'approved_amount': "FLOAT DEFAULT 0.0",
                    'rejected_amount': "FLOAT DEFAULT 0.0", 
                    'pending_amount': "FLOAT DEFAULT 0.0",
                    'finance_status': "VARCHAR(20) NULL",
                    'being_processed_by': "INT NULL",
                    'processing_started_at': "DATETIME NULL"
                }
                
                for col in missing_columns:
                    if col in column_definitions:
                        print(f"ALTER TABLE epv ADD COLUMN {col} {column_definitions[col]};")
            
            return missing_columns
            
    except Exception as e:
        print(f"❌ Error checking EPV table: {e}")
        return []

def main():
    """Main function"""
    print("🔗 Connecting to Production Database...")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   User: {DB_CONFIG['user']}")
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        sys.exit(1)
    
    try:
        # Show all tables
        all_tables = show_all_tables(connection)
        
        # Check EPV application tables
        found_tables, missing_tables = check_app_related_tables(connection, all_tables)
        
        # If EPV table exists, check its columns
        if 'epv' in found_tables:
            missing_columns = check_epv_table_columns(connection)
        
        # Show structure of key tables
        key_tables = ['epv', 'costcenter', 'employee_details']
        for table in key_tables:
            if table in all_tables:
                show_table_structure(connection, table)
        
        print(f"\n✅ Database analysis complete!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    
    finally:
        connection.close()
        print(f"\n🔌 Database connection closed.")

if __name__ == "__main__":
    main()

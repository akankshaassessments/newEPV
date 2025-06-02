#!/usr/bin/env python3
"""
⚠️  DANGER: This script will DROP all EPV-related tables and DELETE ALL DATA!
Only run this if you want to completely reset the EPV application database.
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

def drop_epv_tables(connection):
    """Drop all EPV-related tables in the correct order (to handle foreign keys)"""
    
    # Tables to drop in order (child tables first to avoid foreign key constraints)
    epv_tables = [
        'supplementary_document',    # References epv
        'finance_entry',            # References epv and employee_details
        'epv_approval',             # References epv and epv_allocation
        'epv_allocation',           # References epv and costcenter
        'epv_item',                 # References epv
        'epv',                      # Main EPV table
        'expense_head',             # Standalone table
        'settings_finance',         # Standalone table
        'city_assignment',          # References employee_details
        'costcenter',               # Referenced by epv
        'employee_details',         # Referenced by various tables
        'oauth',                    # References users
        'users'                     # User authentication
    ]
    
    print(f"\n⚠️  WARNING: About to drop {len(epv_tables)} EPV-related tables!")
    print("This will DELETE ALL EPV application data permanently!")
    print("\nTables to be dropped:")
    for i, table in enumerate(epv_tables, 1):
        print(f"{i:2d}. {table}")
    
    # Ask for confirmation
    print(f"\n🚨 FINAL WARNING: This action cannot be undone!")
    confirmation = input("Type 'DELETE ALL EPV DATA' to confirm (anything else will cancel): ")
    
    if confirmation != 'DELETE ALL EPV DATA':
        print("❌ Operation cancelled. No tables were dropped.")
        return False
    
    print(f"\n🗑️  Starting to drop tables...")
    
    dropped_tables = []
    failed_tables = []
    
    try:
        with connection.cursor() as cursor:
            # Disable foreign key checks temporarily
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            print("🔓 Disabled foreign key checks")
            
            for table in epv_tables:
                try:
                    # Check if table exists first
                    cursor.execute(f"SHOW TABLES LIKE '{table}'")
                    if cursor.fetchone():
                        cursor.execute(f"DROP TABLE {table}")
                        dropped_tables.append(table)
                        print(f"✅ Dropped table: {table}")
                    else:
                        print(f"⚠️  Table {table} does not exist, skipping...")
                        
                except Exception as e:
                    failed_tables.append((table, str(e)))
                    print(f"❌ Failed to drop {table}: {e}")
            
            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            print("🔒 Re-enabled foreign key checks")
            
            # Commit the changes
            connection.commit()
            
    except Exception as e:
        print(f"❌ Error during table dropping: {e}")
        connection.rollback()
        return False
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Successfully dropped: {len(dropped_tables)} tables")
    print(f"   Failed to drop: {len(failed_tables)} tables")
    
    if dropped_tables:
        print(f"\n✅ Successfully dropped tables:")
        for table in dropped_tables:
            print(f"   - {table}")
    
    if failed_tables:
        print(f"\n❌ Failed to drop tables:")
        for table, error in failed_tables:
            print(f"   - {table}: {error}")
    
    return len(failed_tables) == 0

def verify_tables_dropped(connection):
    """Verify that EPV tables have been dropped"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            remaining_tables = [table[0] for table in cursor.fetchall()]
            
            epv_table_names = [
                'supplementary_document', 'finance_entry', 'epv_approval', 
                'epv_allocation', 'epv_item', 'epv', 'expense_head', 
                'settings_finance', 'city_assignment', 'costcenter', 
                'employee_details', 'oauth', 'users'
            ]
            
            remaining_epv_tables = [table for table in remaining_tables if table in epv_table_names]
            
            print(f"\n🔍 Verification:")
            if remaining_epv_tables:
                print(f"❌ Some EPV tables still exist:")
                for table in remaining_epv_tables:
                    print(f"   - {table}")
            else:
                print(f"✅ All EPV tables have been successfully dropped!")
                
            print(f"\n📋 Remaining tables in database:")
            for table in remaining_tables:
                print(f"   - {table}")
                
    except Exception as e:
        print(f"❌ Error during verification: {e}")

def main():
    """Main function"""
    print("🗑️  EPV Tables Deletion Script")
    print("=" * 40)
    print(f"Database: {DB_CONFIG['database']}")
    print(f"Host: {DB_CONFIG['host']}")
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        sys.exit(1)
    
    try:
        # Drop EPV tables
        success = drop_epv_tables(connection)
        
        if success:
            # Verify tables are dropped
            verify_tables_dropped(connection)
            print(f"\n🎉 EPV tables deletion completed successfully!")
            print(f"💡 You can now run your app's init_db() to recreate clean tables.")
        else:
            print(f"\n❌ Some errors occurred during table deletion.")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    finally:
        connection.close()
        print(f"\n🔌 Database connection closed.")

if __name__ == "__main__":
    print("⚠️  DANGER ZONE: This script will delete ALL EPV application data!")
    print("Make sure you have a backup if you need to recover the data.")
    print()
    
    proceed = input("Do you want to continue? (type 'yes' to proceed): ")
    if proceed.lower() != 'yes':
        print("❌ Operation cancelled.")
        sys.exit(0)
    
    main()

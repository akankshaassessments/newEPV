#!/usr/bin/env python3
"""
Script to drop User and OAuth tables from server database
Since we're now using EmployeeDetails for Flask-Login
"""
import pymysql

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

def drop_user_tables(connection):
    """Drop User and OAuth tables"""
    
    tables_to_drop = ['oauth', 'users']  # Drop oauth first due to foreign key
    
    print(f"\n🗑️ About to drop User authentication tables:")
    for table in tables_to_drop:
        print(f"   - {table}")
    
    confirmation = input("\nType 'DROP USER TABLES' to confirm: ")
    if confirmation != 'DROP USER TABLES':
        print("❌ Operation cancelled")
        return False
    
    try:
        with connection.cursor() as cursor:
            # Disable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            for table in tables_to_drop:
                try:
                    cursor.execute(f"SHOW TABLES LIKE '{table}'")
                    if cursor.fetchone():
                        cursor.execute(f"DROP TABLE {table}")
                        print(f"✅ Dropped table: {table}")
                    else:
                        print(f"⚠️ Table {table} does not exist")
                except Exception as e:
                    print(f"❌ Error dropping {table}: {e}")
            
            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            connection.commit()
            
        print(f"\n🎉 User tables cleanup completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        connection.rollback()
        return False

def main():
    print("🗑️ User Tables Cleanup Script")
    print("=" * 40)
    print("This will drop the 'users' and 'oauth' tables since we're now")
    print("using EmployeeDetails for Flask-Login authentication.")
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        success = drop_user_tables(connection)
        if success:
            print("\n✅ Cleanup completed successfully!")
            print("Your application now uses EmployeeDetails for authentication.")
        else:
            print("\n❌ Cleanup failed!")
    finally:
        connection.close()

if __name__ == "__main__":
    main()

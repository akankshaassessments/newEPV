#!/usr/bin/env python3
"""
Script to copy users table from local database to server database
"""
import pymysql
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Local database configuration (from your .env file)
LOCAL_DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'charset': 'utf8mb4'
}

# Server database configuration
SERVER_DB_CONFIG = {
    'host': '190.92.174.212',
    'port': 3306,
    'user': 'webappor_IT',
    'password': 'Motoming@123',
    'database': 'webappor_AFDW',
    'charset': 'utf8mb4'
}

def connect_to_database(config, name):
    """Connect to a MySQL database"""
    try:
        connection = pymysql.connect(**config)
        print(f"✅ Connected to {name} database: {config['database']}")
        return connection
    except Exception as e:
        print(f"❌ Error connecting to {name} database: {e}")
        return None

def get_table_structure(connection, table_name):
    """Get the CREATE TABLE statement for a table"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW CREATE TABLE {table_name}")
            result = cursor.fetchone()
            if result:
                return result[1]  # The CREATE TABLE statement
            return None
    except Exception as e:
        print(f"❌ Error getting table structure for {table_name}: {e}")
        return None

def get_table_data(connection, table_name):
    """Get all data from a table"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table_name}")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return columns, rows
    except Exception as e:
        print(f"❌ Error getting data from {table_name}: {e}")
        return None, None

def create_table_on_server(server_connection, create_statement):
    """Create table on server using CREATE TABLE statement"""
    try:
        # Fix collation issues by replacing newer collations with compatible ones
        fixed_statement = create_statement.replace('utf8mb4_0900_ai_ci', 'utf8mb4_general_ci')
        fixed_statement = fixed_statement.replace('utf8_0900_ai_ci', 'utf8_general_ci')

        print(f"📝 Fixed CREATE statement for server compatibility")

        with server_connection.cursor() as cursor:
            cursor.execute(fixed_statement)
            server_connection.commit()
            print("✅ Table structure created on server")
            return True
    except Exception as e:
        print(f"❌ Error creating table on server: {e}")
        print(f"Statement: {fixed_statement}")
        return False

def insert_data_to_server(server_connection, table_name, columns, rows):
    """Insert data into server table"""
    if not rows:
        print("ℹ️  No data to insert")
        return True
    
    try:
        with server_connection.cursor() as cursor:
            # Create INSERT statement
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            
            # Insert all rows
            cursor.executemany(insert_sql, rows)
            server_connection.commit()
            
            print(f"✅ Inserted {len(rows)} rows into {table_name}")
            return True
            
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
        server_connection.rollback()
        return False

def copy_users_table():
    """Main function to copy users table from local to server"""
    
    print("🔄 Copying users table from local to server...")
    print(f"Local DB: {LOCAL_DB_CONFIG['database']} @ {LOCAL_DB_CONFIG['host']}")
    print(f"Server DB: {SERVER_DB_CONFIG['database']} @ {SERVER_DB_CONFIG['host']}")
    
    # Connect to both databases
    local_conn = connect_to_database(LOCAL_DB_CONFIG, "local")
    if not local_conn:
        print("❌ Cannot connect to local database. Check your .env file.")
        return False
    
    server_conn = connect_to_database(SERVER_DB_CONFIG, "server")
    if not server_conn:
        print("❌ Cannot connect to server database.")
        local_conn.close()
        return False
    
    try:
        # Check if users table exists in local database
        with local_conn.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'users'")
            if not cursor.fetchone():
                print("❌ Users table not found in local database")
                return False
        
        print("✅ Users table found in local database")
        
        # Get table structure from local
        print("📋 Getting table structure...")
        create_statement = get_table_structure(local_conn, 'users')
        if not create_statement:
            print("❌ Could not get table structure")
            return False
        
        print("✅ Got table structure")
        
        # Get data from local users table
        print("📊 Getting data from local users table...")
        columns, rows = get_table_data(local_conn, 'users')
        if columns is None:
            print("❌ Could not get data from local users table")
            return False
        
        print(f"✅ Got {len(rows)} rows from local users table")
        
        # Check if users table exists on server and drop it if it does
        with server_conn.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'users'")
            if cursor.fetchone():
                print("⚠️  Users table exists on server, dropping it...")
                cursor.execute("DROP TABLE users")
                server_conn.commit()
                print("✅ Dropped existing users table")
        
        # Create table on server
        print("🏗️  Creating users table on server...")
        if not create_table_on_server(server_conn, create_statement):
            return False
        
        # Insert data to server
        print("📤 Inserting data to server...")
        if not insert_data_to_server(server_conn, 'users', columns, rows):
            return False
        
        # Verify the copy
        print("🔍 Verifying copy...")
        with server_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users")
            server_count = cursor.fetchone()[0]
            
        print(f"✅ Verification: {server_count} rows in server users table")
        
        if server_count == len(rows):
            print("🎉 Users table successfully copied to server!")
            return True
        else:
            print("❌ Row count mismatch - copy may be incomplete")
            return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    finally:
        local_conn.close()
        server_conn.close()
        print("🔌 Database connections closed")

def show_users_data():
    """Show what users data will be copied"""
    print("👥 Checking local users data...")
    
    local_conn = connect_to_database(LOCAL_DB_CONFIG, "local")
    if not local_conn:
        return
    
    try:
        with local_conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            
            if users:
                print(f"\n📋 Found {len(users)} users in local database:")
                print("-" * 60)
                for user in users:
                    print(f"ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}")
            else:
                print("ℹ️  No users found in local database")
                
    except Exception as e:
        print(f"❌ Error checking users: {e}")
    
    finally:
        local_conn.close()

def main():
    """Main function"""
    print("👥 Users Table Copy Script")
    print("=" * 40)
    
    # Show what will be copied
    show_users_data()
    
    print(f"\n⚠️  This will:")
    print("1. Drop the existing users table on server (if it exists)")
    print("2. Create a new users table with local structure")
    print("3. Copy all user data from local to server")
    
    proceed = input("\nDo you want to proceed? (type 'yes' to continue): ")
    if proceed.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    # Copy the table
    success = copy_users_table()
    
    if success:
        print("\n🎉 Users table copy completed successfully!")
    else:
        print("\n❌ Users table copy failed!")

if __name__ == "__main__":
    main()

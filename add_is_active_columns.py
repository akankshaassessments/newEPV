import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Motoming@123',
    'db': 'AFDW',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def add_is_active_columns():
    """Add is_active columns to costcenter and employee_details tables if they don't exist."""
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        
        with connection.cursor() as cursor:
            # Check if the column already exists in costcenter table
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'costcenter'
                AND COLUMN_NAME = 'is_active'
            """, (db_config['db']))
            
            result = cursor.fetchone()
            
            if result['count'] == 0:
                print("Adding is_active column to costcenter table...")
                # Add the column
                cursor.execute("""
                    ALTER TABLE costcenter
                    ADD COLUMN is_active BOOLEAN DEFAULT TRUE
                """)
                connection.commit()
                print("Column added successfully to costcenter table!")
            else:
                print("is_active column already exists in costcenter table.")
            
            # Check if the column already exists in employee_details table
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'employee_details'
                AND COLUMN_NAME = 'is_active'
            """, (db_config['db']))
            
            result = cursor.fetchone()
            
            if result['count'] == 0:
                print("Adding is_active column to employee_details table...")
                # Add the column
                cursor.execute("""
                    ALTER TABLE employee_details
                    ADD COLUMN is_active BOOLEAN DEFAULT TRUE
                """)
                connection.commit()
                print("Column added successfully to employee_details table!")
            else:
                print("is_active column already exists in employee_details table.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        connection.close()

if __name__ == "__main__":
    add_is_active_columns()

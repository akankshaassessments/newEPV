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

def add_split_invoice_column():
    """Add the split_invoice column to the epv_item table if it doesn't exist."""
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        
        with connection.cursor() as cursor:
            # Check if the column already exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'epv_item'
                AND COLUMN_NAME = 'split_invoice'
            """, (db_config['db']))
            
            result = cursor.fetchone()
            
            if result['count'] == 0:
                print("Adding split_invoice column to epv_item table...")
                # Add the column
                cursor.execute("""
                    ALTER TABLE epv_item
                    ADD COLUMN split_invoice BOOLEAN DEFAULT FALSE
                """)
                connection.commit()
                print("Column added successfully!")
            else:
                print("split_invoice column already exists in epv_item table.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        connection.close()

if __name__ == "__main__":
    add_split_invoice_column()

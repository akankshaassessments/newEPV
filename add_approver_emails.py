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

def add_approver_emails_column():
    """Add the approver_emails column to the EPV table."""
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        
        with connection.cursor() as cursor:
            # Check if the column already exists
            cursor.execute("SHOW COLUMNS FROM epv LIKE 'approver_emails'")
            column_exists = cursor.fetchone()
            
            if not column_exists:
                # Add the column
                sql = "ALTER TABLE epv ADD COLUMN approver_emails TEXT AFTER status"
                cursor.execute(sql)
                connection.commit()
                print("Successfully added 'approver_emails' column to the EPV table.")
            else:
                print("Column 'approver_emails' already exists in the EPV table.")
        
    except Exception as e:
        print(f"Error adding column: {str(e)}")
    finally:
        connection.close()

if __name__ == "__main__":
    add_approver_emails_column()

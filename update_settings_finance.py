import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Motoming@123')
DB_NAME = os.getenv('DB_NAME', 'AFDW')
DB_PORT = int(os.getenv('DB_PORT', '3306'))

# Connect to the database
try:
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    print(f"Connected to database {DB_NAME} on {DB_HOST}")
    
    # Create a cursor
    with connection.cursor() as cursor:
        # Check if the columns already exist
        cursor.execute("SHOW COLUMNS FROM settings_finance LIKE 'updated_by'")
        updated_by_exists = cursor.fetchone()
        
        cursor.execute("SHOW COLUMNS FROM settings_finance LIKE 'updated_on'")
        updated_on_exists = cursor.fetchone()
        
        cursor.execute("SHOW COLUMNS FROM settings_finance LIKE 'previous_value'")
        previous_value_exists = cursor.fetchone()
        
        # Add columns if they don't exist
        if not updated_by_exists:
            print("Adding 'updated_by' column to settings_finance table...")
            cursor.execute("ALTER TABLE settings_finance ADD COLUMN updated_by VARCHAR(100) NULL")
        
        if not updated_on_exists:
            print("Adding 'updated_on' column to settings_finance table...")
            cursor.execute("ALTER TABLE settings_finance ADD COLUMN updated_on DATETIME NULL")
        
        if not previous_value_exists:
            print("Adding 'previous_value' column to settings_finance table...")
            cursor.execute("ALTER TABLE settings_finance ADD COLUMN previous_value VARCHAR(100) NULL")
        
        # Add the max_days setting if it doesn't exist
        cursor.execute("SELECT * FROM settings_finance WHERE setting_name = 'max_days'")
        max_days_exists = cursor.fetchone()
        
        if not max_days_exists:
            print("Adding 'max_days' setting to settings_finance table...")
            cursor.execute("""
                INSERT INTO settings_finance (setting_name, setting_value, description)
                VALUES ('max_days', '5', 'Maximum number of days for processing expenses (SOP)')
            """)
        
        # Commit the changes
        connection.commit()
        
        print("Database update completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
        print("Database connection closed.")

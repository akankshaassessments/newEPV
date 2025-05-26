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
        # Check if the max_days setting exists
        cursor.execute("SELECT * FROM settings_finance WHERE setting_name = 'max_days'")
        max_days = cursor.fetchone()
        
        # Check if the days setting exists (the original setting for past days)
        cursor.execute("SELECT * FROM settings_finance WHERE setting_name = 'days'")
        days = cursor.fetchone()
        
        # Check if max_days_past already exists
        cursor.execute("SELECT * FROM settings_finance WHERE setting_name = 'max_days_past'")
        max_days_past = cursor.fetchone()
        
        if max_days and not max_days_past:
            # Rename max_days to max_days_processing
            print("Renaming 'max_days' to 'max_days_processing'...")
            cursor.execute("""
                UPDATE settings_finance 
                SET setting_name = 'max_days_processing', 
                    description = 'Maximum number of days for processing expenses (SOP)'
                WHERE setting_name = 'max_days'
            """)
        
        if days and not max_days_past:
            # Rename days to max_days_past
            print("Renaming 'days' to 'max_days_past'...")
            cursor.execute("""
                UPDATE settings_finance 
                SET setting_name = 'max_days_past', 
                    description = 'Maximum number of days in the past for expense claims'
                WHERE setting_name = 'days'
            """)
        
        # Commit the changes
        connection.commit()
        
        # Verify the changes
        cursor.execute("SELECT * FROM settings_finance")
        settings = cursor.fetchall()
        print("\nUpdated settings:")
        for setting in settings:
            print(f"{setting['setting_name']}: {setting['setting_value']} - {setting['description']}")
        
        print("\nDatabase update completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
        print("Database connection closed.")

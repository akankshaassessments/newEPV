import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters from environment variables
DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

def run_migration():
    """Add finance rejection columns to EPV table"""
    try:
        # Connect to the database
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )

        with connection.cursor() as cursor:
            # Check if the columns already exist
            cursor.execute("SHOW COLUMNS FROM epv LIKE 'finance_rejected_by'")
            has_finance_rejected_by = cursor.fetchone() is not None

            cursor.execute("SHOW COLUMNS FROM epv LIKE 'finance_rejected_on'")
            has_finance_rejected_on = cursor.fetchone() is not None

            cursor.execute("SHOW COLUMNS FROM epv LIKE 'finance_rejection_reason'")
            has_finance_rejection_reason = cursor.fetchone() is not None

            # Add columns if they don't exist
            if not has_finance_rejected_by:
                print("Adding finance_rejected_by column to EPV table...")
                cursor.execute('ALTER TABLE epv ADD COLUMN finance_rejected_by VARCHAR(100)')
                print("Added finance_rejected_by column to EPV table")
            else:
                print("finance_rejected_by column already exists in EPV table")

            if not has_finance_rejected_on:
                print("Adding finance_rejected_on column to EPV table...")
                cursor.execute('ALTER TABLE epv ADD COLUMN finance_rejected_on DATETIME')
                print("Added finance_rejected_on column to EPV table")
            else:
                print("finance_rejected_on column already exists in EPV table")

            if not has_finance_rejection_reason:
                print("Adding finance_rejection_reason column to EPV table...")
                cursor.execute('ALTER TABLE epv ADD COLUMN finance_rejection_reason TEXT')
                print("Added finance_rejection_reason column to EPV table")
            else:
                print("finance_rejection_reason column already exists in EPV table")

        # Commit the changes
        connection.commit()
        print("Migration completed successfully")
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)

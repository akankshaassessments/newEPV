import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Database connection parameters from environment variables
DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

def run_migration():
    """Add columns to track who is processing an EPV"""
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
            cursor.execute("SHOW COLUMNS FROM epv LIKE 'being_processed_by'")
            has_being_processed_by = cursor.fetchone() is not None

            cursor.execute("SHOW COLUMNS FROM epv LIKE 'processing_started_at'")
            has_processing_started_at = cursor.fetchone() is not None

            # Add columns if they don't exist
            if not has_being_processed_by:
                print("Adding being_processed_by column to EPV table...")
                cursor.execute('ALTER TABLE epv ADD COLUMN being_processed_by INT')
                print("Added being_processed_by column to EPV table")
            else:
                print("being_processed_by column already exists in EPV table")

            if not has_processing_started_at:
                print("Adding processing_started_at column to EPV table...")
                cursor.execute('ALTER TABLE epv ADD COLUMN processing_started_at DATETIME')
                print("Added processing_started_at column to EPV table")
            else:
                print("processing_started_at column already exists in EPV table")

            # Add foreign key constraint if it doesn't exist
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'epv'
                AND COLUMN_NAME = 'being_processed_by'
                AND REFERENCED_TABLE_NAME = 'employee_details'
            """, (DB_NAME,))

            has_fk = cursor.fetchone()[0] > 0

            if not has_fk and has_being_processed_by:
                print("Adding foreign key constraint for being_processed_by column...")
                cursor.execute("""
                    ALTER TABLE epv
                    ADD CONSTRAINT fk_epv_processor
                    FOREIGN KEY (being_processed_by)
                    REFERENCES employee_details(id)
                """)
                print("Added foreign key constraint")
            elif has_fk:
                print("Foreign key constraint already exists")

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

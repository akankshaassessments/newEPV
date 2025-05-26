#!/usr/bin/env python
"""
Add the document_status and requested_documents columns to the EPV table.
"""

import pymysql
import sys

def add_columns():
    """Add the document_status and requested_documents columns to the EPV table."""
    try:
        # Connect to the database
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='Motoming@123',
            database='AFDW'
        )
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Check if the columns already exist
        cursor.execute("SHOW COLUMNS FROM epv LIKE 'document_status'")
        document_status_exists = cursor.fetchone() is not None
        
        cursor.execute("SHOW COLUMNS FROM epv LIKE 'requested_documents'")
        requested_documents_exists = cursor.fetchone() is not None
        
        # Add the columns if they don't exist
        if not document_status_exists:
            print("Adding document_status column...")
            cursor.execute("ALTER TABLE epv ADD COLUMN document_status VARCHAR(50) DEFAULT 'complete'")
        else:
            print("document_status column already exists.")
        
        if not requested_documents_exists:
            print("Adding requested_documents column...")
            cursor.execute("ALTER TABLE epv ADD COLUMN requested_documents TEXT NULL")
        else:
            print("requested_documents column already exists.")
        
        # Commit the changes
        conn.commit()
        
        # Close the connection
        conn.close()
        
        print("Done!")
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    add_columns()

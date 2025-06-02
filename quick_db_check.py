#!/usr/bin/env python3
"""
Quick database check script - Upload this to your server and run it there
"""
import pymysql

def main():
    # Database connection for localhost (when running on server)
    try:
        connection = pymysql.connect(
            host='localhost',
            port=3306,
            user='webappor_IT',
            password='Motoming@123',
            database='webappor_AFDW',
            charset='utf8mb4'
        )
        print("✅ Connected to database successfully!")
        
        with connection.cursor() as cursor:
            # Show all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print(f"\n📋 All tables in database:")
            for i, table in enumerate(tables, 1):
                print(f"{i:2d}. {table[0]}")
            
            # Check if EPV table exists and show its structure
            table_names = [table[0] for table in tables]
            
            if 'epv' in table_names:
                print(f"\n🔍 EPV table structure:")
                cursor.execute("DESCRIBE epv")
                columns = cursor.fetchall()
                
                existing_columns = [col[0] for col in columns]
                print("Existing columns:", existing_columns)
                
                # Check for missing columns
                required_columns = [
                    'document_status', 'requested_documents', 'approved_amount',
                    'rejected_amount', 'pending_amount', 'finance_status',
                    'being_processed_by', 'processing_started_at'
                ]
                
                missing = [col for col in required_columns if col not in existing_columns]
                
                if missing:
                    print(f"\n❌ Missing columns: {missing}")
                    print(f"\n🔧 Run these SQL commands:")
                    print("ALTER TABLE epv ADD COLUMN document_status VARCHAR(50) DEFAULT 'complete';")
                    print("ALTER TABLE epv ADD COLUMN requested_documents TEXT;")
                    print("ALTER TABLE epv ADD COLUMN approved_amount FLOAT DEFAULT 0.0;")
                    print("ALTER TABLE epv ADD COLUMN rejected_amount FLOAT DEFAULT 0.0;")
                    print("ALTER TABLE epv ADD COLUMN pending_amount FLOAT DEFAULT 0.0;")
                    print("ALTER TABLE epv ADD COLUMN finance_status VARCHAR(20);")
                    print("ALTER TABLE epv ADD COLUMN being_processed_by INT;")
                    print("ALTER TABLE epv ADD COLUMN processing_started_at DATETIME;")
                else:
                    print("✅ All required columns exist!")
            else:
                print("❌ EPV table not found!")
        
        connection.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

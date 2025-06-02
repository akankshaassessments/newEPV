#!/usr/bin/env python3
"""
Script to clean up local database - remove User and OAuth tables
"""
import os
import sys
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our models
from models import db

def create_local_app():
    """Create Flask app configured for local database"""
    
    app = Flask(__name__)
    
    # Local database configuration from .env
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '3306')
    db_name = os.environ.get('DB_NAME', 'epv_db')
    
    # URL encode the password to handle special characters
    import urllib.parse

    # Construct database URI
    if db_password:
        encoded_password = urllib.parse.quote_plus(db_password)
        db_uri = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
    else:
        db_uri = f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}"
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'temp-secret-for-cleanup'
    
    # Initialize database with app
    db.init_app(app)
    
    print(f"✅ Flask app configured for local database")
    print(f"   Host: {db_host}")
    print(f"   Database: {db_name}")
    print(f"   User: {db_user}")
    
    return app

def cleanup_local_tables():
    """Remove User and OAuth tables from local database"""
    
    print("🗑️ Cleaning up local database...")
    print("=" * 40)
    
    app = create_local_app()
    
    try:
        with app.app_context():
            # Check if tables exist and drop them
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            tables_to_drop = ['oauth', 'users']
            dropped_tables = []
            
            print(f"📋 Existing tables: {existing_tables}")
            
            for table in tables_to_drop:
                if table in existing_tables:
                    try:
                        # Drop the table using raw SQL with newer SQLAlchemy syntax
                        with db.engine.connect() as conn:
                            conn.execute(db.text(f"DROP TABLE {table}"))
                            conn.commit()
                        dropped_tables.append(table)
                        print(f"✅ Dropped table: {table}")
                    except Exception as e:
                        print(f"❌ Error dropping {table}: {e}")
                else:
                    print(f"ℹ️ Table {table} does not exist")
            
            if dropped_tables:
                print(f"\n🎉 Successfully dropped {len(dropped_tables)} tables from local database!")
            else:
                print(f"\nℹ️ No tables needed to be dropped")
                
            return True
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

def verify_cleanup():
    """Verify that tables were removed"""
    
    print("\n🔍 Verifying cleanup...")
    
    app = create_local_app()
    
    try:
        with app.app_context():
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            user_tables = [t for t in existing_tables if t in ['users', 'oauth']]
            
            if user_tables:
                print(f"⚠️ Some user tables still exist: {user_tables}")
                return False
            else:
                print(f"✅ All user tables successfully removed!")
                print(f"📋 Remaining tables: {existing_tables}")
                return True
                
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def main():
    """Main function"""
    print("🧹 Local Database Cleanup Script")
    print("=" * 40)
    print("This will remove 'users' and 'oauth' tables from your local database")
    print("since we're now using EmployeeDetails for authentication.")
    print()
    
    proceed = input("Do you want to proceed? (type 'yes' to continue): ")
    if proceed.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    # Clean up tables
    success = cleanup_local_tables()
    
    if success:
        # Verify cleanup
        verify_cleanup()
        print("\n🎉 Local database cleanup completed!")
        print("Your local database now matches the server structure.")
    else:
        print("\n❌ Cleanup failed!")

if __name__ == "__main__":
    main()

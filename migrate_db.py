import os
import pymysql
from sqlalchemy import text
from flask import Flask
from models import db, init_db, CityAssignment, FinanceEntry

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

# Database configuration
# Get database credentials from environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT', '3306')
db_name = os.environ.get('DB_NAME')

# URL encode the password to handle special characters like @
import urllib.parse
encoded_password = urllib.parse.quote_plus(db_password) if db_password else ''

# Construct the database URI
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
with app.app_context():
    db.init_app(app)

    # Add finance_status column to EPV table if it doesn't exist
    print("Adding finance_status column to EPV table...")
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE epv ADD COLUMN finance_status VARCHAR(20) NULL"))
            conn.commit()
        print("finance_status column added successfully.")
    except Exception as e:
        print(f"Error adding finance_status column: {str(e)}")
        print("Column may already exist or there was an error.")

    # Create all tables
    print("Creating new tables...")
    try:
        db.create_all()
        print("Tables created successfully.")
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        print("Tables may already exist or there was an error.")

    print("Migration completed.")

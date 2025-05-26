#!/usr/bin/env python
"""
Update the SQLAlchemy model cache to reflect the new columns in the EPV table.
"""

import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database credentials from environment variables
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'Motoming@123')
DB_NAME = os.environ.get('DB_NAME', 'AFDW')

# Create the database connection string
db_uri = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Create the engine
engine = create_engine(db_uri)

# Create a base class for declarative models
Base = declarative_base()

# Define the EPV model with the new columns
class EPV(Base):
    __tablename__ = 'epv'
    
    id = Column(String(50), primary_key=True)
    document_status = Column(String(50), default='complete')
    requested_documents = Column(Text, nullable=True)
    
    # Add other columns as needed, but we only need the primary key and the new columns

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Reflect the existing table
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    # Check if the columns exist
    epv_table = metadata.tables['epv']
    document_status_exists = 'document_status' in epv_table.columns
    requested_documents_exists = 'requested_documents' in epv_table.columns
    
    print(f"document_status column exists: {document_status_exists}")
    print(f"requested_documents column exists: {requested_documents_exists}")
    
    # If the columns don't exist, add them
    if not document_status_exists or not requested_documents_exists:
        print("Adding missing columns...")
        
        # Create a connection
        conn = engine.connect()
        
        # Add the columns
        if not document_status_exists:
            conn.execute("ALTER TABLE epv ADD COLUMN document_status VARCHAR(50) DEFAULT 'complete'")
            print("Added document_status column")
        
        if not requested_documents_exists:
            conn.execute("ALTER TABLE epv ADD COLUMN requested_documents TEXT NULL")
            print("Added requested_documents column")
        
        # Commit the changes
        conn.close()
        
        print("Columns added successfully!")
    else:
        print("All columns already exist.")
    
    # Force SQLAlchemy to update its model cache
    print("Updating SQLAlchemy model cache...")
    Base.metadata.create_all(engine)
    
    print("Done!")
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1)
finally:
    session.close()

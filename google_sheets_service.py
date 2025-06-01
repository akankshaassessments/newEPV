"""
Google Sheets Service Module
============================

This module provides functions to interact with Google Sheets API
for reading data from spreadsheets.

Requirements:
    - Google Sheets API enabled in Google Cloud Console
    - Service account credentials or OAuth credentials
    - google-api-python-client package
"""

import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_google_sheets_service():
    """
    Get authenticated Google Sheets service object
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Sheets service
    """
    creds = None
    
    # Method 1: Try service account credentials (recommended for production)
    service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service-account-key.json')
    if os.path.exists(service_account_file):
        print(f"Using service account credentials from: {service_account_file}")
        creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    
    # Method 2: Try OAuth credentials (for development)
    elif os.path.exists('token.json'):
        print("Using OAuth credentials from token.json")
        creds = OAuthCredentials.from_authorized_user_file('token.json', SCOPES)
    
    # Method 3: Try environment variable for service account JSON
    elif os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'):
        print("Using service account credentials from environment variable")
        service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    
    # If no valid credentials, try to get them
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            # Try OAuth flow (requires credentials.json)
            if os.path.exists('credentials.json'):
                print("Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            else:
                raise Exception(
                    "No valid Google credentials found. Please provide one of:\n"
                    "1. Service account key file (service-account-key.json)\n"
                    "2. OAuth credentials file (credentials.json)\n"
                    "3. Environment variable GOOGLE_SERVICE_ACCOUNT_JSON\n"
                    "4. Existing token file (token.json)"
                )
    
    # Build and return the service
    service = build('sheets', 'v4', credentials=creds)
    return service

def read_sheet_data(spreadsheet_id, range_name):
    """
    Read data from a Google Sheet
    
    Args:
        spreadsheet_id (str): The ID of the spreadsheet
        range_name (str): The range to read (e.g., 'Sheet1!A1:D10')
    
    Returns:
        list: List of rows, where each row is a list of cell values
    """
    try:
        service = get_google_sheets_service()
        
        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        return values
        
    except Exception as e:
        print(f"Error reading sheet data: {str(e)}")
        raise

def get_sheet_info(spreadsheet_id):
    """
    Get information about a spreadsheet (sheet names, etc.)
    
    Args:
        spreadsheet_id (str): The ID of the spreadsheet
    
    Returns:
        dict: Spreadsheet metadata
    """
    try:
        service = get_google_sheets_service()
        
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        return {
            'title': spreadsheet.get('properties', {}).get('title', 'Unknown'),
            'sheets': [
                {
                    'title': sheet.get('properties', {}).get('title', 'Unknown'),
                    'sheetId': sheet.get('properties', {}).get('sheetId'),
                    'gridProperties': sheet.get('properties', {}).get('gridProperties', {})
                }
                for sheet in spreadsheet.get('sheets', [])
            ]
        }
        
    except Exception as e:
        print(f"Error getting sheet info: {str(e)}")
        raise

# Example usage and testing
if __name__ == "__main__":
    # Test the Google Sheets service
    try:
        service = get_google_sheets_service()
        print("✅ Google Sheets service initialized successfully!")
        
        # Test with the cost center spreadsheet
        spreadsheet_id = "1XQPqaNKMT2GJ8ajnfm5SZOk6onnnBYJ5SHQSwk_qxJo"
        
        # Get spreadsheet info
        info = get_sheet_info(spreadsheet_id)
        print(f"📊 Spreadsheet: {info['title']}")
        print("📋 Available sheets:")
        for sheet in info['sheets']:
            print(f"   - {sheet['title']}")
        
        # Try to read the Cost Center sheet
        try:
            data = read_sheet_data(spreadsheet_id, "Cost Center!A1:Z100")
            print(f"📈 Successfully read {len(data)} rows from Cost Center sheet")
            if data:
                print(f"📝 Headers: {data[0]}")
        except Exception as e:
            print(f"❌ Could not read Cost Center sheet: {str(e)}")
            
    except Exception as e:
        print(f"❌ Failed to initialize Google Sheets service: {str(e)}")
        print("\n🔧 Setup instructions:")
        print("1. Enable Google Sheets API in Google Cloud Console")
        print("2. Create service account and download key file as 'service-account-key.json'")
        print("3. Or create OAuth credentials and download as 'credentials.json'")
        print("4. Share the Google Sheet with the service account email")

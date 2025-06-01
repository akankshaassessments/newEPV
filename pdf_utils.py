#!/usr/bin/env python
"""
Utility functions for handling PDF files, including merging and uploading to Google Drive.
"""

import os
import io
import uuid
import tempfile
from datetime import datetime
from PyPDF2 import PdfMerger, PdfReader
from werkzeug.utils import secure_filename
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from flask import session

def validate_pdf(file):
    """
    Validate if the uploaded file is a valid PDF.

    Args:
        file: The uploaded file object

    Returns:
        True if valid PDF, False otherwise
    """
    try:
        # Save current position
        current_position = file.tell()

        # Read the file content
        file.seek(0)
        file_content = file.read()

        # Reset file position
        file.seek(current_position)

        # Check if file is empty
        if len(file_content) == 0:
            print("ERROR: PDF file is empty")
            return False

        # Check PDF header
        if not file_content.startswith(b'%PDF-'):
            print("ERROR: File does not have PDF header")
            return False

        # Try to read the PDF with PyPDF2
        try:
            # Create a BytesIO object from the file content
            pdf_stream = io.BytesIO(file_content)
            pdf_reader = PdfReader(pdf_stream)

            # Check if PDF has pages
            if len(pdf_reader.pages) == 0:
                print("ERROR: PDF has no pages")
                return False

            # Try to read the first page (this will catch most corruption issues)
            first_page = pdf_reader.pages[0]

            print(f"✅ PDF validation successful: {len(pdf_reader.pages)} pages")
            return True

        except Exception as pdf_error:
            print(f"ERROR: PDF validation failed: {str(pdf_error)}")
            return False

    except Exception as e:
        print(f"ERROR: File validation failed: {str(e)}")
        return False

def merge_pdfs(pdf_files, output_path):
    """
    Merge multiple PDF files into a single PDF.

    Args:
        pdf_files: List of PDF file paths to merge
        output_path: Path where the merged PDF should be saved

    Returns:
        True if successful, False otherwise
    """
    try:
        if not pdf_files:
            print("ERROR: No PDF files provided for merging")
            return False

        # Create a PDF merger
        merger = PdfMerger()

        # Add each PDF file to the merger
        for pdf_file in pdf_files:
            if not os.path.exists(pdf_file):
                print(f"WARNING: PDF file not found: {pdf_file}")
                continue

            try:
                merger.append(pdf_file)
                print(f"✅ Added to merger: {pdf_file}")
            except Exception as e:
                print(f"ERROR: Failed to add {pdf_file} to merger: {str(e)}")
                continue

        # Write the merged PDF
        merger.write(output_path)
        merger.close()

        print(f"✅ Successfully merged PDFs to: {output_path}")
        return True

    except Exception as e:
        print(f"ERROR: PDF merging failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def download_from_drive(file_id, output_path):
    """
    Download a file from Google Drive.

    Args:
        file_id: The ID of the file in Google Drive
        output_path: The path where the file should be saved

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if we have Google token in session
        if 'google_token' not in session:
            print("ERROR: No Google token in session")
            return False

        # Create credentials from session token
        credentials = Credentials(
            token=session['google_token']['access_token'],
            refresh_token=session['google_token']['refresh_token'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
        )

        # Build the Drive API client
        drive_service = build('drive', 'v3', credentials=credentials)

        # Download the file
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.FileIO(output_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.close()

        print(f"Successfully downloaded file from Drive: {output_path}")
        return True
    except Exception as e:
        print(f"Error downloading file from Drive: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def upload_to_drive(file_path, filename, parent_folder_id):
    """
    Upload a file to Google Drive.

    Args:
        file_path: The path to the file to upload
        filename: The name to give the file in Google Drive
        parent_folder_id: The ID of the folder to upload to

    Returns:
        The ID of the uploaded file, or None if upload failed
    """
    try:
        # Check if we have Google token in session
        if 'google_token' not in session:
            print("ERROR: No Google token in session")
            return None

        # Create credentials from session token
        credentials = Credentials(
            token=session['google_token']['access_token'],
            refresh_token=session['google_token']['refresh_token'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
        )

        # Build the Drive API client
        drive_service = build('drive', 'v3', credentials=credentials)

        # File metadata
        file_metadata = {
            'name': filename,
            'parents': [parent_folder_id]
        }

        # Upload the file
        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"Successfully uploaded file to Drive: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        print(f"Error uploading file to Drive: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

def merge_supplementary_documents(epv, supplementary_files, upload_folder):
    """
    Merge supplementary documents with the original EPV document.

    Args:
        epv: The EPV record
        supplementary_files: A list of tuples (filename, file_path) of supplementary files
        upload_folder: The folder where uploaded files are stored

    Returns:
        The path to the merged PDF, or None if merging failed
    """
    try:
        # Create a unique filename for the merged PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_hex = uuid.uuid4().hex[:8]
        merged_pdf_path = os.path.join(upload_folder, f"merged_{epv.epv_id}_{timestamp}_{random_hex}.pdf")

        # Create a PDF merger
        merger = PdfMerger()

        # Download the original PDF from Google Drive if available
        original_pdf_path = None
        if epv.drive_file_id:
            try:
                # Create a temporary file for the original PDF
                original_pdf_path = os.path.join(upload_folder, f"original_{epv.epv_id}_{random_hex}.pdf")

                # Download the file from Google Drive
                success = download_from_drive(epv.drive_file_id, original_pdf_path)
                if success:
                    print(f"Downloaded original PDF from Drive: {original_pdf_path}")

                    # Add the original PDF to the merger
                    merger.append(original_pdf_path)
                else:
                    print("Failed to download original PDF from Drive")
            except Exception as e:
                print(f"Error downloading original PDF: {str(e)}")
                import traceback
                print(traceback.format_exc())

        # Add each supplementary file to the merger
        for filename, file_path in supplementary_files:
            try:
                if file_path.lower().endswith('.pdf'):
                    merger.append(file_path)
                    print(f"Added supplementary PDF to merger: {file_path}")
                else:
                    # Convert non-PDF files to PDF
                    from pdf_converter import convert_to_pdf
                    pdf_path = convert_to_pdf(file_path)
                    if pdf_path:
                        merger.append(pdf_path)
                        print(f"Added converted PDF to merger: {pdf_path}")
                    else:
                        print(f"Failed to convert {file_path} to PDF")
            except Exception as e:
                print(f"Error adding {file_path} to merger: {str(e)}")

        # Write the merged PDF
        merger.write(merged_pdf_path)
        merger.close()

        print(f"Successfully merged PDFs: {merged_pdf_path}")
        return merged_pdf_path
    except Exception as e:
        print(f"Error merging PDFs: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

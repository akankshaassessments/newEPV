import os
import uuid
import tempfile
import sys
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import url_for

# Import Jinja2 for templating
try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    print("WARNING: Jinja2 not available. PDF document generation will be disabled.")
    JINJA2_AVAILABLE = False

# Try to import HTML to PDF conversion libraries
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    print("WARNING: pdfkit not available. Will try other PDF generation methods.")
    PDFKIT_AVAILABLE = False

# WeasyPrint requires system libraries that might not be available
# Disable it to avoid errors
WEASYPRINT_AVAILABLE = False

# Try to import ReportLab for PDF generation
REPORTLAB_AVAILABLE = False
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    REPORTLAB_AVAILABLE = True
    print("ReportLab successfully imported")
except ImportError as e:
    print(f"WARNING: ReportLab import error: {str(e)}. Will try other PDF generation methods.")

# Import Google Drive utilities
try:
    from drive_utils import upload_file_to_drive, get_file_url
    DRIVE_UTILS_AVAILABLE = True
except ImportError:
    print("WARNING: Google Drive utilities not available. Files will not be uploaded to Drive.")
    DRIVE_UTILS_AVAILABLE = False

# Try to import PDF libraries, but provide fallbacks if they're not available
# Force PyPDF2 to be available since we've installed it
PYPDF2_AVAILABLE = True
try:
    from PyPDF2 import PdfMerger
    print("PyPDF2 successfully imported")
except ImportError as e:
    print(f"WARNING: PyPDF2 import error: {str(e)}. PDF merging will be disabled.")
    PYPDF2_AVAILABLE = False

# Force img2pdf to be available since we've installed it
IMG2PDF_AVAILABLE = True
try:
    import img2pdf
    print("img2pdf successfully imported")
except ImportError as e:
    print(f"WARNING: img2pdf import error: {str(e)}. Will use PIL for image conversion.")
    IMG2PDF_AVAILABLE = False

# Force PIL to be available since we've installed it
PIL_AVAILABLE = True
try:
    from PIL import Image
    print("PIL successfully imported")
except ImportError as e:
    print(f"WARNING: PIL import error: {str(e)}. Image conversion will be disabled.")
    PIL_AVAILABLE = False

# Create directories for uploads, templates, and static files
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf_uploads')
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Create directories if they don't exist
for directory in [UPLOAD_DIR, STATIC_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, mode=0o777)  # Full permissions to ensure writability

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_expense_document(expense_data):
    """
    Generate a PDF document from expense data using ReportLab directly

    Args:
        expense_data: Dictionary containing expense information

    Returns:
        Path to the generated PDF file, or None if generation failed
    """
    try:
        # Create a unique filename for the expense document
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        # Use a temporary file instead of saving to UPLOAD_DIR
        temp_dir = tempfile.gettempdir()
        output_pdf = os.path.join(temp_dir, f"{timestamp}_{unique_id}_expense_document.pdf")

        # Prepare data for the PDF
        data = expense_data.copy()

        # Calculate total amount if not already provided
        if 'total_amount' not in data:
            total_amount = 0
            for expense in data.get('expenses', []):
                try:
                    amount = float(expense.get('amount', 0))
                    total_amount += amount
                except (ValueError, TypeError):
                    pass

            data['total_amount'] = f"{total_amount:.2f}"

            # Always generate amount in words using our utility function
            from utils import number_to_words
            data['amount_in_words'] = number_to_words(total_amount)

        # Set current date if not provided
        if 'current_date' not in data:
            data['current_date'] = datetime.now().strftime('%d/%m/%Y')

        # Generate PDF directly using ReportLab
        if not REPORTLAB_AVAILABLE:
            print("ReportLab is not available. Cannot generate expense document.")
            return None

        try:
            # Import required modules
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, cm
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.platypus.flowables import HRFlowable

            # Create the document
            doc = SimpleDocTemplate(output_pdf, pagesize=letter)
            elements = []

            # Styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            subtitle_style = styles['Heading2']
            normal_style = styles['Normal']

            # Generate a unique EPV ID if not provided
            # Format: EPV-YYYYMMDD-CC-XXXXXXXXXX (CC is cost center code, 10 hex chars from UUID for near-absolute uniqueness)
            if 'epv_id' not in data:
                # Extract cost center code from cost center name if available
                cost_center = data.get('cost_center', '')

                # Generate a distinctive cost center code
                if cost_center:
                    # Handle special cases with underscores
                    if '_' in cost_center:
                        parts = cost_center.split('_')
                        if len(parts) >= 2:
                            # Take first character(s) from first part and first character(s) from second part
                            first_part = ''.join([c for c in parts[0] if c.isalpha() or c.isdigit()])[:2]
                            second_part = ''.join([c for c in parts[1] if c.isalpha() or c.isdigit()])[:2]
                            cost_center_code = (first_part + second_part).upper()
                        else:
                            cost_center_code = ''.join([c for c in cost_center.upper() if c.isalpha() or c.isdigit()])[:4]
                    else:
                        cost_center_code = ''.join([c for c in cost_center.upper() if c.isalpha() or c.isdigit()])[:4]
                else:
                    cost_center_code = 'GEN'  # Generic code if no cost center provided

                epv_id = 'EPV-' + datetime.now().strftime('%Y%m%d') + '-' + cost_center_code + '-' + uuid.uuid4().hex[:10].upper()
            else:
                epv_id = data.get('epv_id')

            # Store the EPV ID in the data dictionary for later use
            if 'epv_id' not in data:
                data['epv_id'] = epv_id

            # Add title with today's date and EPV ID
            today_date = datetime.now().strftime('%d-%m-%Y')

            # Add a colored header line at the extreme top
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.blue, spaceBefore=0, spaceAfter=0.2*inch))

            # Add logo
            logo_path = '/Users/admin/Downloads/EPV/static/images/logo.png'
            if os.path.exists(logo_path):
                print(f"DEBUG: Logo found at {logo_path}")
                logo = Image(logo_path, width=1.5*inch, height=0.75*inch)
                elements.append(logo)
                elements.append(Spacer(1, 0.1*inch))
            else:
                print(f"DEBUG: Logo not found at {logo_path}")

            # Create a table for the header with title, date and EPV ID
            header_style = ParagraphStyle(
                'Header',
                parent=title_style,
                textColor=colors.blue,
                fontSize=16,
                spaceAfter=12
            )

            header_data = [
                [Paragraph("Expense Report", header_style), Paragraph(f"Date: {today_date}", normal_style)],
                [Paragraph(f"EPV ID: {epv_id}", normal_style), ""]
            ]

            header_table = Table(header_data, colWidths=[4*inch, 3*inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (1, 1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (0, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ]))

            elements.append(header_table)
            elements.append(Spacer(1, 0.25*inch))

            # Add employee info in a table with 2 elements per row

            # Format from_date and to_date to dd-mm-yyyy if they're in yyyy-mm-dd format
            from_date = data.get('from_date', '')
            to_date = data.get('to_date', '')

            try:
                # Handle datetime objects
                if isinstance(from_date, datetime):
                    from_date = from_date.strftime('%d-%m-%Y')
                # Handle string dates
                elif isinstance(from_date, str) and from_date and '-' in from_date and len(from_date.split('-')[0]) == 4:
                    date_obj = datetime.strptime(from_date, '%Y-%m-%d')
                    from_date = date_obj.strftime('%d-%m-%Y')
            except Exception as e:
                print(f"Error formatting from_date: {e}")

            try:
                # Handle datetime objects
                if isinstance(to_date, datetime):
                    to_date = to_date.strftime('%d-%m-%Y')
                # Handle string dates
                elif isinstance(to_date, str) and to_date and '-' in to_date and len(to_date.split('-')[0]) == 4:
                    date_obj = datetime.strptime(to_date, '%Y-%m-%d')
                    to_date = date_obj.strftime('%d-%m-%Y')
            except Exception as e:
                print(f"Error formatting to_date: {e}")

            info_data = [
                [Paragraph("<b>Employee ID:</b>", normal_style), data.get('employee_id', ''),
                 Paragraph("<b>Employee Name:</b>", normal_style), data.get('employee_name', '')],
                [Paragraph("<b>Cost Center:</b>", normal_style), data.get('cost_center', ''),
                 Paragraph("<b>Expense Type:</b>", normal_style), data.get('expense_type', '')],
                [Paragraph("<b>From Date:</b>", normal_style), from_date,
                 Paragraph("<b>To Date:</b>", normal_style), to_date],
            ]

            info_table = Table(info_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.5*inch))

            # Add expenses subtitle
            elements.append(Paragraph("Expense Details", subtitle_style))
            elements.append(Spacer(1, 0.25*inch))

            # Add expenses table with improved styling
            expense_data = [['#', 'Date', 'Expense Head', 'Description', 'Amount (₹)']]

            for i, expense in enumerate(data.get('expenses', [])):
                # Format the invoice date to dd-mm-yyyy if it's in yyyy-mm-dd format
                invoice_date = expense.get('invoice_date', '')
                try:
                    # Handle datetime objects
                    if isinstance(invoice_date, datetime):
                        invoice_date = invoice_date.strftime('%d-%m-%Y')
                    # Handle string dates
                    elif isinstance(invoice_date, str) and invoice_date and '-' in invoice_date:
                        # Check if it's in yyyy-mm-dd format
                        if len(invoice_date.split('-')[0]) == 4:
                            date_obj = datetime.strptime(invoice_date, '%Y-%m-%d')
                            invoice_date = date_obj.strftime('%d-%m-%Y')
                except Exception as e:
                    print(f"Error formatting date: {e}")

                expense_data.append([
                    str(i+1),
                    invoice_date,
                    expense.get('expense_head', ''),
                    expense.get('description', ''),
                    expense.get('amount', '')
                ])

            # Add total row
            expense_data.append(['', '', '', 'Total:', data.get('total_amount', '')])

            # Adjust row heights to ensure up to 10 rows can fit on a single page
            row_height = 0.3*inch  # Reduced row height to fit more rows
            expense_table = Table(expense_data,
                                 colWidths=[0.5*inch, 1*inch, 1.5*inch, 3*inch, 1*inch],
                                 rowHeights=[0.4*inch] + [row_height] * (len(expense_data) - 2) + [0.4*inch])

            expense_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),

                # Zebra striping for data rows
                ('BACKGROUND', (0, 1), (-1, -2), colors.white),
                # Apply light grey to even rows (starting from row 2)
                *[('BACKGROUND', (0, i), (-1, i), colors.lightgrey) for i in range(2, len(expense_data)-1, 2)],

                # Total row styling
                ('BACKGROUND', (-2, -1), (-1, -1), colors.lightblue),
                ('TEXTCOLOR', (-2, -1), (-1, -1), colors.darkblue),
                ('FONT', (-2, -1), (-1, -1), 'Helvetica-Bold'),

                # General styling
                ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),  # Right-align amounts
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.blue),
                ('LINEBELOW', (0, -1), (-1, -1), 1, colors.blue),
                ('PADDING', (0, 0), (-1, -1), 4),  # Reduced padding to fit more content
            ]))
            elements.append(expense_table)
            elements.append(Spacer(1, 0.25*inch))

            # Add split invoice allocation details if this is a split invoice
            if data.get('is_split_invoice') and data.get('split_allocations'):
                # Add split allocations subtitle
                elements.append(Paragraph("Split Invoice Allocation Details", subtitle_style))
                elements.append(Spacer(1, 0.15*inch))

                # Create allocation table
                allocation_data = [['#', 'Cost Center', 'Amount (₹)', 'Expense Head', 'Approver']]

                for i, allocation in enumerate(data.get('split_allocations', [])):
                    allocation_data.append([
                        str(i+1),
                        allocation.get('cost_center', ''),
                        f"{allocation.get('amount', 0):.2f}",
                        allocation.get('expense_head', ''),
                        allocation.get('approver', '')
                    ])

                # Create allocation table with appropriate styling
                allocation_table = Table(allocation_data,
                                       colWidths=[0.5*inch, 1.5*inch, 1*inch, 1.5*inch, 2.5*inch],
                                       rowHeights=[0.4*inch] + [0.3*inch] * (len(allocation_data) - 1))

                allocation_table.setStyle(TableStyle([
                    # Header row styling
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),

                    # Zebra striping for data rows
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    # Apply light grey to even rows
                    *[('BACKGROUND', (0, i), (-1, i), colors.lightgrey) for i in range(2, len(allocation_data), 2)],

                    # General styling
                    ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Right-align amounts
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('PADDING', (0, 0), (-1, -1), 4),
                ]))

                elements.append(allocation_table)
                elements.append(Spacer(1, 0.25*inch))

            # Add amount in words with styling
            amount_in_words_para = Paragraph(
                f"<b>Amount in words:</b> <i>{data.get('amount_in_words', '')}</i>",
                normal_style
            )
            elements.append(amount_in_words_para)

            # Calculate remaining space to push footer to bottom
            # For a standard A4 page (8.27 × 11.69 inches), with margins and existing content

            # Get the number of expense rows (excluding header and total)
            num_expense_rows = len(data.get('expenses', []))

            # Get the number of allocation rows if this is a split invoice
            num_allocation_rows = 0
            allocation_table_height = 0
            if data.get('is_split_invoice') and data.get('split_allocations'):
                num_allocation_rows = len(data.get('split_allocations', []))
                allocation_table_height = (
                    0.25 +        # Subtitle
                    0.15 +        # Spacer
                    (num_allocation_rows + 1) * 0.3 +  # Allocation table (rows + header)
                    0.25          # Spacer
                )

            # Calculate the approximate height used so far
            # Logo + header + info table + expense table + allocation table (if split) + amount in words
            used_height = (
                0.75 + 0.1 +  # Logo height + spacer
                0.5 +         # Header table
                0.25 +        # Spacer
                1.0 +         # Info table (approximate)
                0.5 +         # Spacer
                0.25 +        # Subtitle
                0.25 +        # Spacer
                (num_expense_rows + 2) * row_height +  # Expense table (rows + header + total)
                0.25 +        # Spacer
                allocation_table_height +  # Split allocation table (if applicable)
                0.5           # Amount in words
            )

            # A4 page height is approximately 11 inches, minus margins (1 inch top, 1 inch bottom)
            available_height = 9.0  # inches

            # Calculate remaining space needed to push footer to bottom
            remaining_space = max(0, available_height - used_height)

            # Add a dynamic spacer to push footer to bottom
            elements.append(Spacer(1, remaining_space * inch))

            # Add a colored footer line at the extreme bottom
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.blue, spaceAfter=0.1*inch))

            # Add footer with EPV ID
            footer_style = ParagraphStyle(
                'Footer',
                parent=normal_style,
                textColor=colors.darkblue,
                alignment=1,  # Center alignment
                fontSize=8
            )

            # Add current date and EPV ID in footer
            footer_text = f"Generated on {today_date} | EPV ID: {epv_id}"
            elements.append(Paragraph(footer_text, footer_style))

            # Build the PDF
            doc.build(elements)
            print(f"Generated expense document PDF using ReportLab: {output_pdf}")
            return output_pdf

        except Exception as e:
            print(f"Error generating PDF with ReportLab: {str(e)}")
            return None

    except Exception as e:
        print(f"Error generating expense document: {str(e)}")
        return None

def convert_to_pdf(file_path):
    """
    Convert a file to PDF

    Args:
        file_path: Path to the file to convert

    Returns:
        Path to the converted PDF file, or None if conversion failed
    """
    if not file_path or not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None

    # If the file is already a PDF, just return it
    if file_path.lower().endswith('.pdf'):
        print(f"File is already a PDF: {file_path}")
        return file_path

    # Get the file extension
    file_ext = os.path.splitext(file_path)[1].lower()

    # Create a PDF filename
    pdf_path = os.path.splitext(file_path)[0] + '.pdf'

    try:
        # Method 1: Use img2pdf for image conversion (best quality)
        if IMG2PDF_AVAILABLE and file_ext in ['.jpg', '.jpeg', '.png']:
            try:
                print(f"Converting {file_path} to PDF using img2pdf")
                with open(file_path, "rb") as image_file:
                    pdf_bytes = img2pdf.convert(image_file.read())
                    with open(pdf_path, "wb") as pdf_file:
                        pdf_file.write(pdf_bytes)

                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                    print(f"Successfully converted to PDF: {pdf_path}")
                    return pdf_path
            except Exception as e:
                print(f"Error converting with img2pdf: {str(e)}")

        # Method 2: Use PIL for image conversion
        if PIL_AVAILABLE and file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
            try:
                print(f"Converting {file_path} to PDF using PIL")
                image = Image.open(file_path)

                # Convert to RGB if the image is in RGBA mode (e.g., PNG with transparency)
                if image.mode == 'RGBA':
                    image = image.convert('RGB')

                image.save(pdf_path, "PDF", resolution=100.0)

                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                    print(f"Successfully converted to PDF: {pdf_path}")
                    return pdf_path
            except Exception as e:
                print(f"Error converting with PIL: {str(e)}")

        # If we get here, conversion failed
        print(f"Failed to convert {file_path} to PDF")
        return None

    except Exception as e:
        print(f"Unexpected error converting to PDF: {str(e)}")
        return None

def merge_pdfs(pdf_files):
    """
    Merge multiple PDF files into one

    Args:
        pdf_files: List of PDF file paths to merge

    Returns:
        Path to the merged PDF file, or None if merging failed
    """
    if not pdf_files:
        print("No PDF files to merge")
        return None

    # If there's only one PDF, just return it
    if len(pdf_files) == 1:
        print(f"Only one PDF file, no need to merge: {pdf_files[0]}")
        return pdf_files[0]

    # Check if PyPDF2 is available
    if not PYPDF2_AVAILABLE:
        print("PyPDF2 not available, cannot merge PDFs")
        return pdf_files[0]  # Return the first PDF

    try:
        # Create a merger object
        merger = PdfMerger()

        # Add each PDF to the merger
        for pdf in pdf_files:
            if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                try:
                    merger.append(pdf)
                    print(f"Added {pdf} to merger")
                except Exception as e:
                    print(f"Error adding {pdf} to merger: {str(e)}")

        # Create a unique filename for the merged PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        merged_filename = f"merged_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
        merged_path = os.path.join(UPLOAD_DIR, merged_filename)

        # Write the merged PDF to file
        merger.write(merged_path)
        merger.close()

        if os.path.exists(merged_path) and os.path.getsize(merged_path) > 0:
            print(f"Successfully merged PDFs: {merged_path}")
            return merged_path
        else:
            print(f"Failed to create merged PDF: {merged_path}")
            return None

    except Exception as e:
        print(f"Error merging PDFs: {str(e)}")
        return None

def process_files(files, drive_folder_id=None, employee_name=None, cost_center_name=None, expense_pdf_path=None):
    """
    Process uploaded files: save them, convert to PDF, merge into one PDF, and upload to Google Drive

    Args:
        files: List of file objects from request.files
        drive_folder_id: ID of the Google Drive folder to upload to (optional)
        employee_name: Name of the employee for file naming (optional)
        cost_center_name: Name of the cost center for file naming (optional)
        expense_pdf_path: Path to the expense document PDF to include at the top (optional)

    Returns:
        Dictionary with processing results
    """
    if not files:
        print("No files provided to process_files function")
        return {
            'success': False,
            'error': 'No files provided',
            'user_message': 'No files were uploaded. Please select at least one file.'
        }

    print(f"Processing {len(files)} files in process_files function")
    for i, file in enumerate(files):
        print(f"File {i+1}: {file.filename if hasattr(file, 'filename') else 'No filename'}")

    # Track processing results for each file
    processing_results = []

    try:
        # Save each file and convert to PDF
        saved_files = []
        pdf_files = []

        # If expense_pdf_path is provided, add it to the beginning of pdf_files
        if expense_pdf_path and os.path.exists(expense_pdf_path):
            pdf_files.append(expense_pdf_path)
            print(f"Added expense document PDF to the beginning: {expense_pdf_path}")

        for file in files:
            # Skip the expense PDF path if it's already in pdf_files
            if isinstance(file, str) and file == expense_pdf_path:
                continue

            # Handle string file paths (already existing files)
            if isinstance(file, str) and os.path.exists(file):
                file_result = {
                    'original_filename': os.path.basename(file),
                    'success': False
                }
                processing_results.append(file_result)

                # If it's already a PDF, just add it to pdf_files
                if file.lower().endswith('.pdf'):
                    pdf_files.append(file)
                    file_result['pdf_path'] = file
                    file_result['success'] = True
                else:
                    # Try to convert to PDF
                    pdf_path = convert_to_pdf(file)
                    if pdf_path:
                        pdf_files.append(pdf_path)
                        file_result['pdf_path'] = pdf_path
                        file_result['success'] = True
            # Handle file objects from request.files
            elif file and hasattr(file, 'filename') and file.filename and allowed_file(file.filename):
                file_result = {
                    'filename': file.filename,
                    'success': False,
                    'error': None,
                    'saved_path': None,
                    'pdf_path': None
                }

                try:
                    # Create a unique filename
                    original_filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_id = uuid.uuid4().hex[:8]
                    unique_filename = f"{timestamp}_{unique_id}_{original_filename}"
                    file_path = os.path.join(UPLOAD_DIR, unique_filename)

                    # Save the file
                    file.save(file_path)
                    saved_files.append(file_path)
                    file_result['saved_path'] = file_path

                    # Convert to PDF
                    pdf_path = convert_to_pdf(file_path)
                    if pdf_path:
                        pdf_files.append(pdf_path)
                        file_result['pdf_path'] = pdf_path
                        file_result['success'] = True

                        # Remove the original file if it's different from the PDF
                        if pdf_path != file_path and os.path.exists(file_path):
                            os.remove(file_path)
                    else:
                        file_result['error'] = 'Failed to convert file to PDF'

                except Exception as e:
                    error_msg = f"Error processing file {file.filename}: {str(e)}"
                    print(error_msg)
                    file_result['error'] = error_msg

                processing_results.append(file_result)
            else:
                # Invalid file
                processing_results.append({
                    'filename': file.filename if hasattr(file, 'filename') and file.filename else 'Unknown file',
                    'success': False,
                    'error': 'Invalid file or file type not allowed',
                    'saved_path': None,
                    'pdf_path': None
                })

        # Check if any files were processed successfully
        if not pdf_files:
            # No PDFs were created
            error_details = []
            for result in processing_results:
                if not result['success'] and result['error']:
                    error_details.append(f"{result['filename']}: {result['error']}")

            error_message = "Failed to convert any files to PDF"
            if error_details:
                error_message += ". Details: " + "; ".join(error_details)

            return {
                'success': False,
                'error': error_message,
                'user_message': 'There was a problem converting your files to PDF. Please try again with different files.',
                'processing_results': processing_results
            }

        # No need to generate expense document here anymore
        # It's now handled in the app.py route

        # Merge PDFs if there are any
        merged_pdf = None
        merge_error = None
        if pdf_files:
            try:
                merged_pdf = merge_pdfs(pdf_files)
                if not merged_pdf:
                    merge_error = "Failed to merge PDF files"
            except Exception as e:
                merge_error = f"Error merging PDFs: {str(e)}"
                print(merge_error)

            # Clean up individual PDF files if merging was successful
            if merged_pdf and merged_pdf not in pdf_files:
                for pdf in pdf_files:
                    if os.path.exists(pdf):
                        os.remove(pdf)

        # Upload to Google Drive if a folder ID is provided and the merged PDF exists
        drive_file_id = None
        drive_file_url = None
        drive_error = None

        # Check if we should attempt Google Drive upload
        drive_upload_attempted = False

        if merged_pdf and drive_folder_id and DRIVE_UTILS_AVAILABLE:
            drive_upload_attempted = True
            try:
                print(f"Uploading merged PDF to Google Drive folder: {drive_folder_id}")

                # Validate drive folder ID
                if not drive_folder_id or drive_folder_id.strip() == "":
                    drive_error = "Google Drive folder ID is empty or invalid"
                    print(f"ERROR: {drive_error}")
                else:
                    # Create a meaningful filename
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    filename_parts = []

                    if employee_name:
                        filename_parts.append(f"Expense_{employee_name}")
                    else:
                        filename_parts.append("Expense")

                    if cost_center_name:
                        filename_parts.append(cost_center_name)

                    filename_parts.append(date_str)
                    drive_filename = "_".join(filename_parts) + ".pdf"

                    print(f"DEBUG: Uploading file with name: {drive_filename}")

                    # Upload to Google Drive
                    drive_file_id = upload_file_to_drive(merged_pdf, drive_filename, drive_folder_id)

                    if drive_file_id and drive_file_id != 'local_file':
                        print(f"SUCCESS: Uploaded to Drive with ID: {drive_file_id}")
                        # Get the file URL
                        drive_file_url = get_file_url(drive_file_id)
                        if drive_file_url:
                            print(f"SUCCESS: Drive file URL: {drive_file_url}")
                        else:
                            print("WARNING: Could not retrieve Drive file URL")
                    elif drive_file_id == 'local_file':
                        print(f"INFO: File saved locally instead of uploading to Google Drive: {merged_pdf}")
                        # No error, just a different path
                        drive_file_id = None
                        drive_error = "The file was saved locally instead of being uploaded to Google Drive. You can download it below."
                    else:
                        drive_error = "Failed to upload file to Google Drive. The upload process did not return a file ID."
                        print(f"ERROR: {drive_error}")
            except Exception as e:
                error_details = str(e)
                if "invalid_grant" in error_details.lower():
                    drive_error = "Google Drive authentication failed. Please ask your administrator to refresh the Google API credentials."
                elif "permission" in error_details.lower():
                    drive_error = "Permission denied when uploading to Google Drive. Please check folder permissions."
                elif "not found" in error_details.lower() or "404" in error_details:
                    drive_error = f"Google Drive folder not found: {drive_folder_id}"
                else:
                    drive_error = f"Error uploading to Google Drive: {error_details}"
                print(f"ERROR: {drive_error}")
        elif not DRIVE_UTILS_AVAILABLE:
            drive_error = "Google Drive integration is not available. Required libraries are missing."
            print(f"ERROR: {drive_error}")
        elif not drive_folder_id:
            drive_error = "No Google Drive folder ID provided. Check cost center settings."
            print(f"WARNING: {drive_error}")

        # Return the results
        result = {
            'success': merged_pdf is not None,
            'saved_files': saved_files,
            'pdf_files': pdf_files,
            'merged_pdf': merged_pdf,
            'processing_results': processing_results,
            'drive_upload_attempted': drive_upload_attempted
        }

        # Add Drive information if available
        if drive_file_id:
            result['drive_file_id'] = drive_file_id
        if drive_file_url:
            result['drive_file_url'] = drive_file_url

        # Add errors and warnings
        if merge_error:
            result['error'] = merge_error
            result['user_message'] = 'Your files were processed, but there was an issue merging them into a single PDF.'

        if drive_error:
            result['drive_error'] = drive_error
            if not result.get('error'):  # Don't overwrite existing error
                result['user_message'] = 'Your files were processed successfully, but there was an issue uploading to Google Drive.'

        # Add warnings for partially successful processing
        warnings = []
        for file_result in processing_results:
            if not file_result['success']:
                warnings.append(f"Problem with {file_result['filename']}: {file_result['error']}")

        if warnings and merged_pdf:
            result['warnings'] = warnings
            result['user_message'] = 'Some files had issues during processing, but at least one file was converted successfully.'

        return result

    except Exception as e:
        error_msg = f"Error processing files: {str(e)}"
        print(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'user_message': 'An unexpected error occurred while processing your files. Please try again.',
            'processing_results': processing_results
        }

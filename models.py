from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from datetime import datetime
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class CostCenter(db.Model):
    __tablename__ = 'costcenter'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    costcenter = db.Column(db.String(100), nullable=False)
    approver_email = db.Column(db.String(100), nullable=True)  # Email of the cost center approver/administrator
    city = db.Column(db.String(50), nullable=True)
    drive_id = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<CostCenter {self.costcenter}>'

class EmployeeDetails(db.Model):
    __tablename__ = 'employee_details'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    employee_id = db.Column(db.String(50), nullable=True)
    manager = db.Column(db.String(100), nullable=True)  # Manager's email
    manager_name = db.Column(db.String(100), nullable=True)  # Manager's name
    name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(50), nullable=True)  # 'Super Admin', 'School Admin', 'Central Admin', 'Pune Staff', 'Mumbai Staff', 'Finance', 'Finance Approver'
    is_active = db.Column(db.Boolean, default=True)

    # Relationship with assigned cities (for Finance personnel)
    city_assignments = db.relationship('CityAssignment', foreign_keys='CityAssignment.employee_id', backref='employee', lazy=True)

    def __repr__(self):
        return f'<EmployeeDetails {self.name} ({self.email})>'

class CityAssignment(db.Model):
    __tablename__ = 'city_assignment'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee_details.id'), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('employee_details.id'), nullable=True)
    assigned_by_employee = db.relationship('EmployeeDetails', foreign_keys=[assigned_by])
    assigned_on = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<CityAssignment {self.employee_id} - {self.city}>'

class SettingsFinance(db.Model):
    __tablename__ = 'settings_finance'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    setting_name = db.Column(db.String(100), nullable=False, unique=True)
    setting_value = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # Fields for tracking changes
    updated_by = db.Column(db.String(100), nullable=True)  # Email of the user who last updated
    updated_on = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    previous_value = db.Column(db.String(100), nullable=True)  # Store previous value for logging

    def __repr__(self):
        return f'<SettingsFinance {self.setting_name}: {self.setting_value}>'

class ExpenseHead(db.Model):
    __tablename__ = 'expense_head'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    head_name = db.Column(db.String(100), nullable=False)
    head_code = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<ExpenseHead {self.head_name} ({self.head_code})>'

class EPV(db.Model):
    """
    Model to store all expense voucher data
    """
    __tablename__ = 'epv'

    id = db.Column(db.Integer, primary_key=True)
    epv_id = db.Column(db.String(30), unique=True, nullable=False)  # EPV-YYYYMMDD-XXXXXXXXXX format

    # Employee details
    email_id = db.Column(db.String(100), nullable=False)
    employee_name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)

    # Date range
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)

    # Payment and acknowledgement
    payment_to = db.Column(db.String(100), nullable=False)  # Previously expense_type
    acknowledgement = db.Column(db.String(255))  # For any acknowledgement information

    # Document status for supplementary documents
    document_status = db.Column(db.String(50), default='complete')  # 'complete', 'pending_additional_documents'
    requested_documents = db.Column(db.Text, nullable=True)  # JSON string describing what's missing

    # Metadata
    submission_date = db.Column(db.DateTime, default=datetime.now)
    academic_year = db.Column(db.String(20))  # e.g., "2024-2025"

    # Cost center
    cost_center_id = db.Column(db.Integer, db.ForeignKey('costcenter.id'))
    cost_center = db.relationship('CostCenter', backref=db.backref('expenses', lazy=True))
    cost_center_name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=True)  # City for the expense (may differ from cost center's city)

    # File storage details
    file_url = db.Column(db.String(255))  # URL to access the file in Google Drive
    drive_file_id = db.Column(db.String(100))  # Google Drive file ID

    # Financial details
    total_amount = db.Column(db.Float, nullable=False)
    amount_in_words = db.Column(db.String(255))

    # Split invoice support
    invoice_type = db.Column(db.String(20), default='standard')  # standard, master, sub, split
    master_invoice_id = db.Column(db.Integer, db.ForeignKey('epv.id'), nullable=True)  # For sub-invoices, points to master
    master_invoice = db.relationship('EPV', foreign_keys=[master_invoice_id], backref=db.backref('sub_invoices', lazy='joined'), remote_side='EPV.id')
    split_status = db.Column(db.String(20), nullable=True)  # splitting, pending_approval, partially_approved, fully_approved, rejected, processing, completed

    # New split invoice fields for single EPV with multiple approvers
    approved_amount = db.Column(db.Float, default=0.0)  # Total amount approved from allocations
    rejected_amount = db.Column(db.Float, default=0.0)  # Total amount rejected from allocations
    pending_amount = db.Column(db.Float, default=0.0)   # Total amount still pending approval

    # Approval workflow
    status = db.Column(db.String(20), default='submitted')  # submitted, pending_approval, approved, rejected, partially_approved, finance_pending, finance_processed, finance_approved, finance_rejected
    # The overall status is determined by the individual approver statuses in EPVApproval
    # If all approvers approve, status = 'approved'
    # If any approver rejects, status = 'rejected'
    # If some approve and none reject, status = 'partially_approved'

    # Finance processing fields
    finance_status = db.Column(db.String(20), nullable=True)  # pending, processed, approved, rejected

    # Fields to track who is currently processing this EPV
    being_processed_by = db.Column(db.Integer, db.ForeignKey('employee_details.id'), nullable=True)
    processing_started_at = db.Column(db.DateTime, nullable=True)
    processor = db.relationship('EmployeeDetails', foreign_keys=[being_processed_by])

    # Legacy fields (kept for backward compatibility)
    approver_emails = db.Column(db.Text)  # Comma-separated list of approver emails
    approved_by = db.Column(db.String(100))  # Email of the approver
    approved_on = db.Column(db.DateTime)  # When it was approved
    rejected_by = db.Column(db.String(100))  # Email of the person who rejected
    rejected_on = db.Column(db.DateTime)  # When it was rejected
    rejection_reason = db.Column(db.Text)  # Why it was rejected

    def __repr__(self):
        return f"<EPV {self.epv_id}>"

class FinanceEntry(db.Model):
    __tablename__ = 'finance_entry'
    id = db.Column(db.Integer, primary_key=True)
    epv_id = db.Column(db.Integer, db.ForeignKey('epv.id'), nullable=False)
    epv = db.relationship('EPV', backref=db.backref('finance_entry', uselist=False, lazy=True))

    # Who processed this entry
    finance_user_id = db.Column(db.Integer, db.ForeignKey('employee_details.id'), nullable=False)
    finance_user = db.relationship('EmployeeDetails', foreign_keys=[finance_user_id])

    # Entry details
    entry_date = db.Column(db.DateTime, default=datetime.now)
    vendor_name = db.Column(db.String(100), nullable=False)
    journal_entry = db.Column(db.String(50), nullable=False)
    payment_voucher = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    fcra_status = db.Column(db.String(20), nullable=False)  # 'FCRA', 'Non-FCRA'
    comments = db.Column(db.Text, nullable=True)

    # Partial payment support
    is_partial_payment = db.Column(db.Boolean, default=False)

    # Payment 1 fields
    journal_entry_1 = db.Column(db.String(50), nullable=True)  # Journal entry for first payment
    payment_voucher_1 = db.Column(db.String(50), nullable=True)  # Payment voucher for first payment
    amount_1 = db.Column(db.Float, nullable=True)  # First partial amount
    fcra_status_1 = db.Column(db.String(20), nullable=True)  # FCRA status for first amount
    transaction_id_1 = db.Column(db.String(100), nullable=True)  # Transaction ID for first payment
    payment_date_1 = db.Column(db.DateTime, nullable=True)  # Payment date for first payment

    # Payment 2 fields
    journal_entry_2 = db.Column(db.String(50), nullable=True)  # Journal entry for second payment
    payment_voucher_2 = db.Column(db.String(50), nullable=True)  # Payment voucher for second payment
    amount_2 = db.Column(db.Float, nullable=True)  # Second partial amount
    fcra_status_2 = db.Column(db.String(20), nullable=True)  # FCRA status for second amount
    transaction_id_2 = db.Column(db.String(100), nullable=True)  # Transaction ID for second payment
    payment_date_2 = db.Column(db.DateTime, nullable=True)  # Payment date for second payment

    # Payment details (added fields)
    transaction_id = db.Column(db.String(100), nullable=True)
    payment_date = db.Column(db.DateTime, nullable=True)

    # Approval details
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approver_id = db.Column(db.Integer, db.ForeignKey('employee_details.id'), nullable=True)
    approver = db.relationship('EmployeeDetails', foreign_keys=[approver_id])
    approved_on = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<FinanceEntry {self.id} for EPV {self.epv_id}>'

class EPVApproval(db.Model):
    """
    Model to store approval status for each approver of an EPV
    """
    __tablename__ = 'epv_approval'

    id = db.Column(db.Integer, primary_key=True)
    epv_id = db.Column(db.Integer, db.ForeignKey('epv.id'), nullable=False)
    epv = db.relationship('EPV', backref=db.backref('approvals', lazy=True))

    # Link to allocation for split invoices (nullable for backward compatibility)
    allocation_id = db.Column(db.Integer, db.ForeignKey('epv_allocation.id'), nullable=True)
    allocation = db.relationship('EPVAllocation', backref=db.backref('approval', uselist=False))

    # Approver details
    approver_email = db.Column(db.String(100), nullable=False)
    approver_name = db.Column(db.String(100))

    # Approval status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    action_date = db.Column(db.DateTime)  # When the approver took action
    comments = db.Column(db.Text)  # Any comments from the approver

    # Token for secure approval/rejection links
    token = db.Column(db.String(100), unique=True)

    def __repr__(self):
        return f"<EPVApproval {self.id} for EPV {self.epv_id} by {self.approver_email}>"

class EPVAllocation(db.Model):
    """
    Model to store cost center allocations for split invoices
    Each allocation represents a portion of the total invoice amount allocated to a specific cost center with a designated approver
    """
    __tablename__ = 'epv_allocation'

    id = db.Column(db.Integer, primary_key=True)
    epv_id = db.Column(db.Integer, db.ForeignKey('epv.id'), nullable=False)
    epv = db.relationship('EPV', backref=db.backref('allocations', lazy=True))

    # Cost center details
    cost_center_id = db.Column(db.Integer, db.ForeignKey('costcenter.id'), nullable=False)
    cost_center_name = db.Column(db.String(100), nullable=False)
    cost_center = db.relationship('CostCenter', foreign_keys=[cost_center_id])

    # Allocation details
    allocated_amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    expense_head = db.Column(db.String(100), nullable=True)  # Expense head for this allocation

    # Approver details
    approver_email = db.Column(db.String(100), nullable=False)
    approver_name = db.Column(db.String(100), nullable=True)

    # Approval status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    action_date = db.Column(db.DateTime, nullable=True)  # When the approver took action
    rejection_reason = db.Column(db.Text, nullable=True)  # Reason for rejection if rejected

    # Token for secure approval/rejection links
    token = db.Column(db.String(100), unique=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<EPVAllocation {self.id} for EPV {self.epv_id} - {self.cost_center_name} - ₹{self.allocated_amount}>"

class EPVItem(db.Model):
    """
    Model to store individual expense items within an EPV
    """
    __tablename__ = 'epv_item'

    id = db.Column(db.Integer, primary_key=True)
    epv_id = db.Column(db.Integer, db.ForeignKey('epv.id'), nullable=False)
    epv = db.relationship('EPV', backref=db.backref('items', lazy=True))

    # Expense details
    expense_invoice_date = db.Column(db.Date, nullable=False)  # Renamed from invoice_date
    expense_head = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # Financial details
    gst = db.Column(db.Float, default=0.0)  # GST amount or percentage
    amount = db.Column(db.Float, nullable=False)

    # Receipt details
    receipt_filename = db.Column(db.String(255))
    receipt_path = db.Column(db.String(255))
    receipt_drive_id = db.Column(db.String(100))

    # Split invoice flag
    split_invoice = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<EPVItem {self.id} for EPV {self.epv_id}>"



class SupplementaryDocument(db.Model):
    """
    Model to store supplementary documents for EPVs
    """
    __tablename__ = 'supplementary_document'

    id = db.Column(db.Integer, primary_key=True)
    epv_id = db.Column(db.Integer, db.ForeignKey('epv.id'), nullable=False)
    epv = db.relationship('EPV', backref=db.backref('supplementary_documents', lazy=True))

    # Document details
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    drive_file_id = db.Column(db.String(100), nullable=True)

    # Metadata
    uploaded_by = db.Column(db.String(100), nullable=False)  # Email of the uploader
    uploaded_on = db.Column(db.DateTime, default=datetime.now)
    description = db.Column(db.Text, nullable=True)  # Description of the document

    # Status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected

    def __repr__(self):
        return f"<SupplementaryDocument {self.id} for EPV {self.epv_id}>"

class User(UserMixin, db.Model):
    """User model for Flask-Login"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    role = db.Column(db.String(50))
    employee_id = db.Column(db.String(50))

    def __repr__(self):
        return f'<User {self.email}>'

class OAuth(OAuthConsumerMixin, db.Model):
    """OAuth token storage model"""
    __tablename__ = 'oauth'
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user = db.relationship(User)

def sync_users_from_employee_details():
    """Sync users from EmployeeDetails to User model"""
    # Get all employee details
    employees = EmployeeDetails.query.all()

    # For each employee, create or update a user
    for employee in employees:
        # Check if user already exists
        user = User.query.filter_by(email=employee.email).first()
        if not user:
            # Create new user
            user = User(
                email=employee.email,
                name=employee.name,
                role=employee.role,
                employee_id=employee.employee_id
            )
            db.session.add(user)
        else:
            # Update existing user
            user.name = employee.name
            user.role = employee.role
            user.employee_id = employee.employee_id

    # Commit changes
    db.session.commit()
    print("Users synced from EmployeeDetails.")

def init_db(app):
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()

        print("Database initialized with all tables.")

        inspector = inspect(db.engine)

        # Initialize cost centers if the table is empty
        if not inspector.has_table('costcenter') or CostCenter.query.count() == 0:
            # List of cost centers to add
            cost_centers = [
                "SBP_BP",
                "SBP_Moshi",
                "PKGEMS",
                "ANWEMS",
                "LDRKEMS",
                "LAPMEMS",
                "KCTVN",
                "CSMEMS",
                "BOPEMS",
                "MEMS",
                "Late Baburaoji Bobade NMCPS",
                "Late Gopalrao Moghare (Khadan)",
                "Ramnagar NMCPS (Nagpur)",
                "Rani Durgavati NMCPS (Nagpur)",
                "Rambhau Mhalginagar NMCPS",
                "Babhulban NMCPS (Nagpur)",
                "PE - Pune",
                "NST - Instruction Specialist - Pune",
                "Counselling & Intervention Pune",
                "Operations Pune",
                "NST - Coaches - Nagpur",
                "NST - Coaches - Pune",
                "Operations Nagpur",
                "PE - Nagpur",
                "Counselling & Intervention Nagpur",
                "NST - Instruction Specialist - Nagpur",
                "Community Engagement Pune",
                "Community Engagement Nagpur",
                "Digital Literacy",
                "Vocational Labs",
                "Sports Program",
                "School Management System",
                "CSMEMS learning tour",
                "Knowledge management",
                "Alumni Management System",
                "IT & Tech Infra - SETU",
                "Leads Development & Training",
                "SBP - Government School (Maharashtra)",
                "Student Wellbeing COI Leads",
                "Scholarship - Pune",
                "IT & Tech Infra - MSP",
                "ASE Pune",
                "Art for Akanksha",
                "IT & Tech Infra - ASE",
                "IT & Tech Infra - Admin",
                "Management - CEO",
                "Management - COO",
                "Impact & Research",
                "Donor Relations & Communication",
                "Finance - Central",
                "Central Administration",
                "Human Resources Central",
                "Project Rise",
                "ABC"
            ]

            # Add default city values based on name
            for cc in cost_centers:
                city = "Pune"  # Default city
                if "Nagpur" in cc:
                    city = "Nagpur"

                # Add drive IDs for specific cost centers
                drive_id = None
                if cc == "SBP_BP":
                    drive_id = "1Ku7ai51N19-p3nYViAa1eeooQjWPRUN1"
                elif cc == "KCTVN":
                    drive_id = "1w48U4Kv_zZUhf9-Bwx6df8su8vQEqKvV"

                # Create and add the cost center to the database
                cost_center = CostCenter(costcenter=cc, city=city, drive_id=drive_id)
                db.session.add(cost_center)

            # Commit the changes
            db.session.commit()
            print("Database initialized with cost centers.")

        # Initialize employee details if the table is empty
        print("DEBUG: Checking employee_details table...")
        if not inspector.has_table('employee_details'):
            print("DEBUG: employee_details table does not exist, creating it...")
        elif EmployeeDetails.query.count() == 0:
            print("DEBUG: employee_details table exists but is empty, populating it...")
        else:
            print(f"DEBUG: employee_details table exists and has {EmployeeDetails.query.count()} records.")

        if not inspector.has_table('employee_details') or EmployeeDetails.query.count() == 0:
            # Employee data from the Google Sheet
            employees = [
                {"email": "nikhil.aher@akanksha.org", "employee_id": "NIKAHE160185", "manager": "3df.demo@akanksha.org", "name": "Nikhil Aher", "role": "admin"},
                {"email": "anil.naik@akanksha.org", "employee_id": "CHAAHE", "manager": "fatima.sawant@akanksha.org", "name": "Chaitrali Aher", "role": "Central"},
                {"email": "amit.kashid@akanksha.org", "employee_id": "SHAPAT", "manager": "shruti.das@akanksha.org", "name": "Sharad", "role": "Super Admin"},
                {"email": "shubham.ambolikar@akanksha.org", "employee_id": "MAYGAnJ", "manager": "anchal.wasnik@akanksha.org", "name": "mayur", "role": "Mumbai_FInance"},
                {"email": "ajay.hendre@akanksha.org", "employee_id": "TriDHha1112", "manager": "sushma.pathare@akanksha.org", "name": "Triveni Dhamdhere", "role": "Pune_Finance"},
                {"email": "pramod.giri@akanksha.org", "employee_id": "", "manager": "parijat.prakash@akanksha.org", "name": "", "role": ""},
                {"email": "rebecca.kamble@akanksha.org", "employee_id": "", "manager": "parijat.prakash@akanksha.org", "name": "", "role": ""},
                {"email": "ashwini.mayekar@akanksha.org", "employee_id": "", "manager": "samina.quettawala@akanksha.org", "name": "", "role": ""},
                {"email": "shraddha.morgaonkar@akanksha.org", "employee_id": "", "manager": "shalini.sachdev@akanksha.org", "name": "", "role": ""},
                {"email": "ajay.sonawane@akanksha.org", "employee_id": "", "manager": "shruti.manerker@akanksha.org", "name": "", "role": ""},
                {"email": "kiran.deogadkar@akanksha.org", "employee_id": "", "manager": "shivani.yadav@akanksha.org", "name": "", "role": ""},
                {"email": "rekha.kolsure@akanksha.org", "employee_id": "", "manager": "ritu.pasricha@akanksha.org", "name": "", "role": ""},
                {"email": "priyanka.pachpor@akanksha.org", "employee_id": "", "manager": "Simranjeet.sankat@akanksha.org", "name": "", "role": ""},
                {"email": "aniket.mayekar@akanksha.org", "employee_id": "", "manager": "prachi.mangaonkar@akanksha.org", "name": "", "role": ""},
                {"email": "rohit.talegaonkar@akanksha.org", "employee_id": "", "manager": "nilambari.nair@akanksha.org", "name": "", "role": ""},
                {"email": "pramod.kamble@akanksha.org", "employee_id": "", "manager": "sima.jhaveri@akanksha.org", "name": "", "role": ""},
                {"email": "aishwarya.mestry@akanksha.org", "employee_id": "", "manager": "bhima.jetty@akanksha.org", "name": "", "role": ""},
                {"email": "sushil.joharkar@akanksha.org", "employee_id": "", "manager": "diana.isabel@akanksha.org", "name": "", "role": ""},
                {"email": "santosh.shirwadkar@akanksha.org", "employee_id": "", "manager": "alsana.lakdawala@akanksha.org", "name": "", "role": ""},
                {"email": "suyash.modak@akanksha.org", "employee_id": "", "manager": "nishant.singhania@akanksha.org", "name": "", "role": ""},
                {"email": "lalit.barapatre@akanksha.org", "employee_id": "", "manager": "mamta.sylvester@akanksha.org", "name": "", "role": ""},
                {"email": "chetan.telang@akanksha.org", "employee_id": "", "manager": "harshada.jadhav@akanksha.og", "name": "", "role": ""},
                {"email": "vishnu.hiwale@akanksha.org", "employee_id": "", "manager": "harshada.jadhav@akanksha.org", "name": "", "role": ""},
                {"email": "sunil.kamble@akanksha.org", "employee_id": "", "manager": "mohmmed.ahmedulla@akanksha.org", "name": "", "role": ""},
                {"email": "umesh.shejul@akanksha.org", "employee_id": "", "manager": "merlin1.elias@akanksha.org", "name": "", "role": ""},
                {"email": "Sushant.kesarkar@akanksha.org", "employee_id": "", "manager": "mandira.purohit@akanksha.org", "name": "", "role": ""},
                {"email": "ankita.dawal@akanksha.org", "employee_id": "", "manager": "sakshi.bhatia@akanksha.org", "name": "", "role": ""},
                {"email": "prakash.dhangar@akanksha.org", "employee_id": "", "manager": "prachi.sanghvi@akanksha.org", "name": "", "role": ""}
            ]

            # Add employees to the database
            for emp_data in employees:
                # Convert email to lowercase for consistency
                employee = EmployeeDetails(
                    email=emp_data["email"].lower(),
                    employee_id=emp_data["employee_id"],
                    manager=emp_data["manager"].lower() if emp_data["manager"] else None,
                    name=emp_data["name"],
                    role=emp_data["role"]
                )
                db.session.add(employee)

            # Commit the changes
            db.session.commit()
            print("Database initialized with employee details.")

        # Sync users from employee details
        if inspector.has_table('employee_details') and EmployeeDetails.query.count() > 0:
            sync_users_from_employee_details()

        # Initialize finance settings if the table is empty
        print("DEBUG: Checking settings_finance table...")
        if not inspector.has_table('settings_finance'):
            print("DEBUG: settings_finance table does not exist, creating it...")
        elif SettingsFinance.query.count() == 0:
            print("DEBUG: settings_finance table exists but is empty, populating it...")
        else:
            print(f"DEBUG: settings_finance table exists and has {SettingsFinance.query.count()} records.")

        if not inspector.has_table('settings_finance') or SettingsFinance.query.count() == 0:
            # Finance settings
            settings = [
                {
                    "setting_name": "max_days_past",
                    "setting_value": "30",
                    "description": "Maximum number of days in the past for expense claims"
                },
                {
                    "setting_name": "max_days_processing",
                    "setting_value": "5",
                    "description": "Maximum number of days for processing expenses (SOP)"
                }
            ]

            # Add settings to the database
            for setting_data in settings:
                setting = SettingsFinance(
                    setting_name=setting_data["setting_name"],
                    setting_value=setting_data["setting_value"],
                    description=setting_data["description"]
                )
                db.session.add(setting)

            # Commit the changes
            db.session.commit()
            print("Database initialized with finance settings.")

        # Initialize expense heads if the table is empty
        print("DEBUG: Checking expense_head table...")
        if not inspector.has_table('expense_head'):
            print("DEBUG: expense_head table does not exist, creating it...")
        elif ExpenseHead.query.count() == 0:
            print("DEBUG: expense_head table exists but is empty, populating it...")
        else:
            print(f"DEBUG: expense_head table exists and has {ExpenseHead.query.count()} records.")

        if not inspector.has_table('expense_head') or ExpenseHead.query.count() == 0:
            # Expense head data from the Google Sheet
            expense_heads = [
                {"head_name": "Travel", "head_code": "TRV", "description": "Travel expenses including airfare, train, bus, etc.", "is_active": True},
                {"head_name": "Accommodation", "head_code": "ACC", "description": "Hotel and lodging expenses", "is_active": True},
                {"head_name": "Meals", "head_code": "MEL", "description": "Food and beverage expenses during business trips", "is_active": True},
                {"head_name": "Office Supplies", "head_code": "OFF", "description": "Stationery, printer ink, and other office consumables", "is_active": True},
                {"head_name": "Communication", "head_code": "COM", "description": "Phone bills, internet charges, and other communication expenses", "is_active": True},
                {"head_name": "Training", "head_code": "TRN", "description": "Costs related to workshops, seminars, and professional development", "is_active": True},
                {"head_name": "Equipment", "head_code": "EQP", "description": "Purchase or rental of equipment and hardware", "is_active": True},
                {"head_name": "Software", "head_code": "SFT", "description": "Software licenses and subscriptions", "is_active": True},
                {"head_name": "Miscellaneous", "head_code": "MSC", "description": "Other expenses that don't fit into specific categories", "is_active": True},
                {"head_name": "Transportation", "head_code": "TRN", "description": "Local transportation like taxis, buses, and fuel", "is_active": True}
            ]

            # Add expense heads to the database
            for head_data in expense_heads:
                expense_head = ExpenseHead(
                    head_name=head_data["head_name"],
                    head_code=head_data["head_code"],
                    description=head_data["description"],
                    is_active=head_data["is_active"]
                )
                db.session.add(expense_head)

            # Commit the changes
            db.session.commit()
            print("Database initialized with expense heads.")

        # Add partial payment columns to finance_entry table if they don't exist
        if inspector.has_table('finance_entry'):
            columns = [col['name'] for col in inspector.get_columns('finance_entry')]

            if 'is_partial_payment' not in columns:
                print("Adding is_partial_payment column to finance_entry table")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE finance_entry ADD COLUMN is_partial_payment BOOLEAN DEFAULT FALSE'))
                    conn.commit()
            else:
                print("is_partial_payment column already exists in finance_entry table")

            if 'amount_1' not in columns:
                print("Adding amount_1 column to finance_entry table")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE finance_entry ADD COLUMN amount_1 FLOAT'))
                    conn.commit()
            else:
                print("amount_1 column already exists in finance_entry table")

            if 'fcra_status_1' not in columns:
                print("Adding fcra_status_1 column to finance_entry table")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE finance_entry ADD COLUMN fcra_status_1 VARCHAR(20)'))
                    conn.commit()
            else:
                print("fcra_status_1 column already exists in finance_entry table")

            if 'amount_2' not in columns:
                print("Adding amount_2 column to finance_entry table")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE finance_entry ADD COLUMN amount_2 FLOAT'))
                    conn.commit()
            else:
                print("amount_2 column already exists in finance_entry table")

            if 'fcra_status_2' not in columns:
                print("Adding fcra_status_2 column to finance_entry table")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE finance_entry ADD COLUMN fcra_status_2 VARCHAR(20)'))
                    conn.commit()
            else:
                print("fcra_status_2 column already exists in finance_entry table")

            # Add additional partial payment fields
            additional_fields = [
                ('journal_entry_1', 'VARCHAR(50)', 'Journal Entry 1'),
                ('payment_voucher_1', 'VARCHAR(50)', 'Payment Voucher 1'),
                ('transaction_id_1', 'VARCHAR(100)', 'Transaction ID 1'),
                ('payment_date_1', 'DATETIME', 'Payment Date 1'),
                ('journal_entry_2', 'VARCHAR(50)', 'Journal Entry 2'),
                ('payment_voucher_2', 'VARCHAR(50)', 'Payment Voucher 2'),
                ('transaction_id_2', 'VARCHAR(100)', 'Transaction ID 2'),
                ('payment_date_2', 'DATETIME', 'Payment Date 2')
            ]

            for field_name, field_type, field_desc in additional_fields:
                if field_name not in columns:
                    print(f"Adding {field_name} column to finance_entry table")
                    with db.engine.connect() as conn:
                        conn.execute(db.text(f'ALTER TABLE finance_entry ADD COLUMN {field_name} {field_type}'))
                        conn.commit()
                else:
                    print(f"{field_name} column already exists in finance_entry table")

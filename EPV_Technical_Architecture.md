# EPV System Technical Architecture

## System Architecture Overview

```mermaid
flowchart TD
    A[Client Browser] <--> B[Flask Web Server]
    B <--> C[(MySQL Database)]
    B <--> D[Google OAuth]
    B <--> E[Google Drive API]
    B <--> F[Gmail API]
    
    subgraph "Server Components"
        B
        G[Flask-Login]
        H[SQLAlchemy ORM]
        I[Jinja2 Templates]
        J[PDF Processing]
    end
    
    B --- G
    B --- H
    B --- I
    B --- J
    H --- C
```

## Database Schema

```mermaid
erDiagram
    User {
        int id PK
        string email
        string name
        string role
        datetime created_at
    }
    
    EmployeeDetails {
        int id PK
        string name
        string email
        string employee_id
        string manager
        string manager_name
        string role
        boolean is_active
    }
    
    CostCenter {
        int id PK
        string costcenter
        string city
        string approver_email
        string drive_id
        boolean is_active
    }
    
    ExpenseHead {
        int id PK
        string head_name
        string head_code
        string description
        boolean is_active
    }
    
    EPV {
        int id PK
        string epv_id UK
        string email_id
        int cost_center_id FK
        string cost_center_name
        string status
        string finance_status
        datetime submission_date
        datetime approved_on
        float total_amount
        string invoice_type
        string rejection_reason
        int being_processed_by
        datetime processing_started_at
    }
    
    EPVItem {
        int id PK
        int epv_id FK
        string expense_head
        string description
        float amount
        string document_id
        string document_link
    }
    
    FinanceEntry {
        int id PK
        int epv_id FK
        int finance_user_id FK
        datetime entry_date
        float amount
        string status
        int approver_id FK
        datetime approved_on
        string rejection_reason
    }
    
    CityAssignment {
        int id PK
        int employee_id FK
        string city
        boolean is_active
    }
    
    User ||--o{ EPV : "submits"
    EmployeeDetails ||--o{ FinanceEntry : "processes"
    EmployeeDetails ||--o{ FinanceEntry : "approves"
    CostCenter ||--o{ EPV : "belongs to"
    EPV ||--o{ EPVItem : "contains"
    EPV ||--o{ FinanceEntry : "processed as"
    EmployeeDetails ||--o{ CityAssignment : "assigned to"
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant Google
    participant Database
    
    User->>Browser: Access application
    Browser->>Flask: Request page
    Flask->>Flask: Check session
    Flask->>Browser: Redirect to login
    Browser->>Flask: Request login
    Flask->>Google: Redirect to OAuth
    Google->>Browser: Show login form
    User->>Google: Enter credentials
    Google->>Flask: Return with auth code
    Flask->>Google: Exchange code for token
    Google->>Flask: Return token and user info
    Flask->>Database: Find/create user
    Database->>Flask: Return user record
    Flask->>Flask: Create session
    Flask->>Browser: Redirect to dashboard
```

## Expense Submission Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant Database
    participant GoogleDrive
    participant Email
    
    User->>Browser: Fill expense form
    User->>Browser: Upload documents
    Browser->>Flask: Submit form data
    Flask->>Flask: Validate data
    Flask->>GoogleDrive: Upload documents
    GoogleDrive->>Flask: Return document IDs
    Flask->>Database: Create EPV record
    Flask->>Database: Create EPV items
    Database->>Flask: Confirm creation
    Flask->>Database: Get approver info
    Database->>Flask: Return approver details
    Flask->>Email: Send notification
    Flask->>Browser: Show success message
```

## Finance Processing Flow

```mermaid
sequenceDiagram
    participant Finance
    participant Browser
    participant Flask
    participant Database
    participant Email
    
    Finance->>Browser: View finance dashboard
    Browser->>Flask: Request pending EPVs
    Flask->>Database: Query approved EPVs
    Database->>Flask: Return EPV list
    Flask->>Browser: Display pending EPVs
    Finance->>Browser: Select EPV to process
    Browser->>Flask: Request EPV details
    Flask->>Database: Lock EPV for processing
    Flask->>Browser: Show EPV details
    Finance->>Browser: Enter finance details
    Browser->>Flask: Submit finance entry
    Flask->>Database: Create finance entry
    Flask->>Database: Update EPV status
    Flask->>Email: Notify finance approver
    Flask->>Browser: Show success message
```

## Role-Based Access Control

```mermaid
flowchart TD
    A[User Authentication] --> B{Check Role}
    
    B -->|Regular User| C[User Dashboard]
    C --> C1[View Own EPVs]
    C --> C2[Submit New EPVs]
    C --> C3[View EPV Status]
    
    B -->|Cost Center Approver| D[Cost Center Admin]
    D --> D1[View Cost Center EPVs]
    D --> D2[Approve/Reject EPVs]
    D --> D3[View Cost Center Reports]
    
    B -->|Finance| E[Finance Dashboard]
    E --> E1[View Pending EPVs]
    E --> E2[Process EPVs]
    E --> E3[View Processed EPVs]
    
    B -->|Finance Approver| F[Finance Approver Dashboard]
    F --> F1[View Pending Finance Entries]
    F --> F2[Approve/Reject Entries]
    F --> F3[Manage City Assignments]
    
    B -->|Super Admin| G[Admin Dashboard]
    G --> G1[Manage Cost Centers]
    G --> G2[Manage Employees]
    G --> G3[Manage Expense Heads]
    G --> G4[System Settings]
```

## Data Filtering Logic

```mermaid
flowchart TD
    A[User Accesses Dashboard] --> B{User Role}
    
    B -->|Regular User| C[Filter: User's Own EPVs]
    B -->|Cost Center Approver| D[Filter: Cost Center EPVs]
    B -->|Finance| E[Filter: City-Assigned EPVs]
    B -->|Finance Approver| F[Filter: All EPVs or City-Assigned]
    B -->|Super Admin| G[No Filtering: All EPVs]
    
    C --> H[Apply Additional Filters]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I[Time Period Filter]
    H --> J[Expense Head Filter]
    H --> K[Cost Center Filter]
    H --> L[Status Filter]
    
    I --> M[Display Filtered Results]
    J --> M
    K --> M
    L --> M
```

## Notification System

```mermaid
flowchart TD
    A[System Event] --> B{Event Type}
    
    B -->|EPV Submission| C[Notify Approver]
    B -->|EPV Approval| D[Notify Finance]
    B -->|EPV Rejection| E[Notify Submitter]
    B -->|Finance Entry| F[Notify Finance Approver]
    B -->|Finance Approval| G[Notify Submitter & Finance]
    B -->|Finance Rejection| H[Notify Finance]
    
    C --> I[Email Notification]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    
    C --> J[In-App Notification]
    D --> J
    E --> J
    F --> J
    G --> J
    H --> J
```

## Deployment Architecture

```mermaid
flowchart TD
    A[User Browser] <--> B[cPanel Web Server]
    B --> C[passenger_wsgi.py]
    C --> D[Flask Application]
    D <--> E[(MySQL Database)]
    D <--> F[Google APIs]
    
    subgraph "cPanel Environment"
        B
        C
        D
        G[Python 3.10 Virtual Environment]
        H[Application Files]
        I[Static Files]
        J[Templates]
    end
    
    D --- G
    D --- H
    D --- I
    D --- J
```

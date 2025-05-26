# Expense Processing Voucher (EPV) System Flow Chart

## Overview

This document provides a visual representation of the key workflows in the EPV system, including:

1. User Authentication Flow
2. Expense Submission Process
3. Approval Workflow
4. Finance Processing Flow
5. Cost Center Administration

## 1. User Authentication Flow

```mermaid
flowchart TD
    A[User Visits Site] --> B{Has Active Session?}
    B -->|Yes| C[Access Dashboard]
    B -->|No| D[Redirect to Login]
    D --> E[Google OAuth Login]
    E --> F{First Time User?}
    F -->|Yes| G[Create User Record]
    F -->|No| H[Update User Info]
    G --> I[Set Session Variables]
    H --> I
    I --> J{Check User Role}
    J -->|Regular User| K[User Dashboard]
    J -->|Finance| L[Finance Dashboard]
    J -->|Finance Approver| M[Finance Approver Dashboard]
    J -->|Super Admin| N[Admin Dashboard]
    J -->|Cost Center Approver| O[Cost Center Admin Access]
```

## 2. Expense Submission Process

```mermaid
flowchart TD
    A[User Initiates New Expense] --> B[Fill Expense Form]
    B --> C[Add Expense Items]
    C --> D[Upload Supporting Documents]
    D --> E[Submit Expense]
    E --> F[System Validates Expense]
    F -->|Valid| G[Create EPV Record]
    F -->|Invalid| H[Show Validation Errors]
    H --> B
    G --> I[Set Status to 'Submitted']
    I --> J[Determine Approval Route]
    J --> K[Notify Approver via Email]
    K --> L[Return to Dashboard]
```

## 3. Approval Workflow

```mermaid
flowchart TD
    A[Approver Receives Email] --> B[Click Approval Link]
    B --> C[View EPV Details]
    C --> D{Decision}
    D -->|Approve| E[Update Status to 'Approved']
    D -->|Reject| F[Provide Rejection Reason]
    F --> G[Update Status to 'Rejected']
    G --> H[Send Rejection Notification to Submitter]
    E --> I[Check if Master Invoice]
    I -->|Yes| J[Update Sub-Invoices Status]
    I -->|No| K[Notify Finance Team]
    J --> K
    K --> L[EPV Ready for Finance Processing]
```

## 4. Finance Processing Flow

```mermaid
flowchart TD
    A[Finance User Views Dashboard] --> B[See Pending EPVs]
    B --> C[Select EPV for Processing]
    C --> D[System Locks EPV]
    D --> E[Review EPV Details]
    E --> F{Decision}
    F -->|Process| G[Enter Finance Details]
    F -->|Reject| H[Provide Rejection Reason]
    G --> I[Submit for Finance Approval]
    H --> J[Update Status to 'Rejected']
    J --> K[Send Rejection Notification]
    I --> L[Finance Approver Reviews]
    L --> M{Decision}
    M -->|Approve| N[Update to 'Finance Approved']
    M -->|Reject| O[Provide Rejection Reason]
    O --> P[Update to 'Finance Rejected']
    N --> Q[Mark as Processed]
    P --> R[Notify Submitter]
    Q --> S[Complete Finance Process]
```

## 5. Cost Center Administration

```mermaid
flowchart TD
    A[Cost Center Admin Logs In] --> B[Access Cost Center Admin View]
    B --> C[View EPVs for Their Cost Centers]
    C --> D[Filter EPVs by Status/Date/Type]
    D --> E[View EPV Details]
    E --> F[Monitor Expense Metrics]
    F --> G[Generate Reports]
```

## 6. User Role Access Control

```mermaid
flowchart TD
    A[User Logs In] --> B{Check Role}
    B -->|Regular User| C[View Own EPVs]
    B -->|Cost Center Approver| D[View Cost Center EPVs]
    B -->|Finance| E[Process Approved EPVs]
    B -->|Finance Approver| F[Approve Finance Entries]
    B -->|Super Admin| G[Access All System Functions]
    C --> H[Submit New EPVs]
    D --> I[View EPVs for Assigned Cost Centers]
    E --> J[Process EPVs for Assigned Cities]
    F --> K[Approve/Reject Finance Entries]
    G --> L[Manage System Settings]
```

## 7. Notification System

```mermaid
flowchart TD
    A[System Event Occurs] --> B{Event Type}
    B -->|EPV Submission| C[Notify Approver]
    B -->|EPV Approval| D[Notify Finance]
    B -->|EPV Rejection| E[Notify Submitter]
    B -->|Finance Processing| F[Notify Finance Approver]
    B -->|Finance Approval| G[Notify Submitter]
    B -->|Finance Rejection| H[Notify Submitter and Finance]
    C --> I[Send Email Notification]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J[Update In-App Notifications]
```

## 8. Document Management

```mermaid
flowchart TD
    A[Document Upload] --> B[Store in Google Drive]
    B --> C[Link to EPV Record]
    C --> D[Generate View/Download Links]
    D --> E[Make Available to Authorized Users]
    E --> F{User Action}
    F -->|View| G[Display Document]
    F -->|Download| H[Provide Document File]
```

## Conclusion

This flow chart provides a high-level overview of the key processes in the EPV system. The actual implementation may contain additional details and edge cases not captured in these diagrams.

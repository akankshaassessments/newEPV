# EPV System User Journeys

This document outlines the different user journeys through the EPV (Expense Processing Voucher) system based on user roles.

## 1. Regular User Journey

```mermaid
journey
    title Regular User Journey
    section Authentication
        Login with Google: 5: User
        Access Dashboard: 5: User
    section Expense Submission
        Create New Expense: 5: User
        Fill Expense Details: 4: User
        Upload Supporting Documents: 4: User
        Submit for Approval: 5: User
    section Tracking
        View EPV Records: 5: User
        Check EPV Status: 5: User
        View Rejection Reasons: 3: User
        Resubmit if Needed: 3: User
```

### Regular User Access Permissions:
- Can create and submit new expense vouchers
- Can view their own submitted EPVs
- Can see only cost centers they've submitted EPVs for in the dashboard filters
- Can track the status of their submissions
- Can view rejection reasons if an EPV is rejected
- Can resubmit rejected EPVs with corrections

## 2. Cost Center Approver Journey

```mermaid
journey
    title Cost Center Approver Journey
    section Authentication
        Login with Google: 5: Approver
        Access Dashboard: 5: Approver
    section Regular Tasks
        View Own EPVs: 4: Approver
        Submit Own Expenses: 4: Approver
    section Approval Tasks
        Access Cost Center Admin: 5: Approver
        View Pending Approvals: 5: Approver
        Review EPV Details: 4: Approver
        Approve/Reject EPVs: 5: Approver
        Provide Rejection Reasons: 4: Approver
    section Monitoring
        View Cost Center Metrics: 4: Approver
        Filter EPVs by Status/Date: 4: Approver
```

### Cost Center Approver Access Permissions:
- Has all regular user permissions
- Can access the Cost Center Admin section
- Can view all EPVs submitted for their assigned cost centers
- Can approve or reject EPVs for their cost centers
- Can provide rejection reasons when declining an EPV
- Can view cost center expense metrics and reports
- Can see only cost centers they're approvers for in the dashboard filters

## 3. Finance User Journey

```mermaid
journey
    title Finance User Journey
    section Authentication
        Login with Google: 5: Finance
        Access Finance Dashboard: 5: Finance
    section Processing
        View Pending EPVs: 5: Finance
        Select EPV for Processing: 5: Finance
        Review EPV Details: 4: Finance
        Process or Reject EPV: 5: Finance
        Enter Finance Details: 4: Finance
        Submit for Approval: 5: Finance
    section Tracking
        View Processed EPVs: 4: Finance
        Check Processing Status: 4: Finance
```

### Finance User Access Permissions:
- Can access the Finance Dashboard
- Can view approved EPVs pending finance processing
- Can process EPVs by entering finance details
- Can reject EPVs with reasons if issues are found
- Can submit processed EPVs for finance approval
- Can view all cost centers in the dashboard filters
- Can only see EPVs for their assigned cities

## 4. Finance Approver Journey

```mermaid
journey
    title Finance Approver Journey
    section Authentication
        Login with Google: 5: Finance Approver
        Access Finance Dashboard: 5: Finance Approver
    section Approval
        View Pending Finance Entries: 5: Finance Approver
        Review Finance Details: 4: Finance Approver
        Approve/Reject Entries: 5: Finance Approver
        Provide Rejection Reasons: 4: Finance Approver
    section Administration
        Manage City Assignments: 3: Finance Approver
        View Approval History: 4: Finance Approver
```

### Finance Approver Access Permissions:
- Can access the Finance Dashboard with approver view
- Can view finance entries pending approval
- Can approve or reject finance entries
- Can provide rejection reasons when declining entries
- Can manage city assignments for finance personnel
- Can view approval history and metrics
- Can view all cost centers in the dashboard filters

## 5. Super Admin Journey

```mermaid
journey
    title Super Admin Journey
    section Authentication
        Login with Google: 5: Admin
        Access Dashboard: 5: Admin
    section System Management
        Access Settings: 5: Admin
        Manage Cost Centers: 5: Admin
        Manage Employees: 5: Admin
        Manage Expense Heads: 5: Admin
    section Monitoring
        View All EPVs: 4: Admin
        View System Metrics: 4: Admin
```

### Super Admin Access Permissions:
- Has access to all system functions
- Can manage cost centers (add, edit, deactivate)
- Can manage employees (add, edit, assign roles)
- Can manage expense heads (add, edit, deactivate)
- Can view all EPVs in the system regardless of status
- Can access system settings and configuration
- Can view all cost centers in the dashboard filters

## User Interface Navigation Flows

### 1. Regular User Navigation

```mermaid
flowchart TD
    A[Login] --> B[Dashboard]
    B --> C[New Expense]
    B --> D[EPV Records]
    C --> E[Submit EPV]
    E --> D
    D --> F[View EPV Details]
```

### 2. Cost Center Approver Navigation

```mermaid
flowchart TD
    A[Login] --> B[Dashboard]
    B --> C[New Expense]
    B --> D[EPV Records]
    B --> E[Cost Center Admin]
    E --> F[View Pending Approvals]
    F --> G[Review EPV]
    G --> H[Approve/Reject]
```

### 3. Finance User Navigation

```mermaid
flowchart TD
    A[Login] --> B[Dashboard]
    B --> C[Finance Dashboard]
    C --> D[Pending EPVs Tab]
    C --> E[Processed Tab]
    D --> F[Select EPV]
    F --> G[Process EPV]
    G --> H[Submit for Approval]
```

### 4. Finance Approver Navigation

```mermaid
flowchart TD
    A[Login] --> B[Dashboard]
    B --> C[Finance Dashboard]
    C --> D[Pending Approval Tab]
    C --> E[Approved/Rejected Tab]
    B --> F[City Assignments]
    D --> G[Review Entry]
    G --> H[Approve/Reject]
```

### 5. Super Admin Navigation

```mermaid
flowchart TD
    A[Login] --> B[Dashboard]
    B --> C[Settings]
    C --> D[Cost Centers Tab]
    C --> E[Employees Tab]
    C --> F[Expense Heads Tab]
    D --> G[Add/Edit Cost Center]
    E --> H[Add/Edit Employee]
    F --> I[Add/Edit Expense Head]
```

## Mobile Experience

The EPV system is responsive and provides a mobile-optimized experience with:

- Mobile-friendly forms for expense submission
- Bottom navigation bar for easy access to key functions
- Collapsible admin menu to maintain consistent navbar height
- Touch-friendly UI elements for approval/rejection actions
- Optimized document viewing on mobile devices

#!/usr/bin/env python3
"""
Script to clear all tables except for cost center, user, employees, and expense heads.
This will remove all EPV records, approvals, allocations, finance entries, etc.
while preserving the core reference data.
"""

from app import app, db
from models import (
    EPV, EPVItem, EPVApproval, EPVAllocation, FinanceEntry,
    SupplementaryDocument, CityAssignment, SettingsFinance,
    CostCenter, EmployeeDetails, ExpenseHead
)

def clear_tables():
    """Clear all tables except the specified ones to keep"""

    with app.app_context():
        try:
            print("Starting table cleanup...")
            print("=" * 50)

            # Tables to clear (in order to respect foreign key constraints)
            # EPVApproval must be cleared before EPVAllocation due to foreign key
            tables_to_clear = [
                ('EPVApproval', EPVApproval),
                ('EPVAllocation', EPVAllocation),
                ('EPVItem', EPVItem),
                ('SupplementaryDocument', SupplementaryDocument),
                ('FinanceEntry', FinanceEntry),
                ('EPV', EPV)
            ]

            # Tables to keep (will NOT be cleared)
            tables_to_keep = [
                'CostCenter',
                'EmployeeDetails',
                'ExpenseHead',
                'CityAssignment',
                'SettingsFinance'
            ]

            print("Tables that will be KEPT (not cleared):")
            for table in tables_to_keep:
                print(f"  ✓ {table}")

            print("\nTables that will be CLEARED:")
            for table_name, table_model in tables_to_clear:
                count = table_model.query.count()
                print(f"  ✗ {table_name} ({count} records)")

            print("\n" + "=" * 50)

            # Ask for confirmation
            response = input("Are you sure you want to clear these tables? (yes/no): ").lower().strip()

            if response != 'yes':
                print("Operation cancelled.")
                return

            print("\nClearing tables...")

            # Clear tables in the correct order
            total_deleted = 0
            for table_name, table_model in tables_to_clear:
                try:
                    count_before = table_model.query.count()
                    print(f"Clearing {table_name}... ({count_before} records)")

                    # Special handling for EPV table due to self-referencing foreign key
                    if table_name == 'EPV':
                        # First, clear the master_invoice_id foreign key references
                        print("  - Clearing master_invoice_id references...")
                        db.session.execute(
                            db.text("UPDATE epv SET master_invoice_id = NULL WHERE master_invoice_id IS NOT NULL")
                        )
                        db.session.commit()
                        print("  - Master invoice references cleared")

                    # Delete all records from this table
                    table_model.query.delete()

                    # Commit after each table to avoid issues
                    db.session.commit()

                    count_after = table_model.query.count()
                    deleted = count_before - count_after
                    total_deleted += deleted

                    print(f"  ✓ Cleared {deleted} records from {table_name}")

                except Exception as e:
                    print(f"  ✗ Error clearing {table_name}: {str(e)}")
                    db.session.rollback()
                    raise

            print(f"\n✓ Successfully cleared {total_deleted} total records")
            print("\nVerifying remaining data...")

            # Verify the tables we wanted to keep still have data
            print("\nRemaining data in preserved tables:")
            print(f"  CostCenter: {CostCenter.query.count()} records")
            print(f"  EmployeeDetails: {EmployeeDetails.query.count()} records")
            print(f"  ExpenseHead: {ExpenseHead.query.count()} records")
            print(f"  CityAssignment: {CityAssignment.query.count()} records")
            print(f"  SettingsFinance: {SettingsFinance.query.count()} records")

            # Verify the tables we cleared are empty
            print("\nVerifying cleared tables are empty:")
            for table_name, table_model in tables_to_clear:
                count = table_model.query.count()
                if count == 0:
                    print(f"  ✓ {table_name}: {count} records")
                else:
                    print(f"  ⚠️  {table_name}: {count} records (should be 0)")

            print("\n" + "=" * 50)
            print("✓ Table cleanup completed successfully!")
            print("\nThe following reference data has been preserved:")
            print("  - Cost Centers")
            print("  - Employee Details")
            print("  - Expense Heads")
            print("  - City Assignments")
            print("  - Settings (Finance)")
            print("\nAll EPV records, approvals, allocations, and finance entries have been cleared.")

        except Exception as e:
            print(f"\n❌ Error during table cleanup: {str(e)}")
            db.session.rollback()
            print("All changes have been rolled back.")
            raise

if __name__ == "__main__":
    clear_tables()

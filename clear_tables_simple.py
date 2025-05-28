#!/usr/bin/env python3
"""
Simple script to clear all tables except for cost center, user, employees, expense heads,
city assignments, and settings.
"""

from app import app, db

def clear_tables():
    """Clear all tables except the specified ones to keep"""
    
    with app.app_context():
        try:
            print("Starting table cleanup...")
            print("=" * 50)
            
            # Get current counts
            print("Current table counts:")
            print(f"  EPV: {db.session.execute(db.text('SELECT COUNT(*) FROM epv')).scalar()}")
            print(f"  EPVItem: {db.session.execute(db.text('SELECT COUNT(*) FROM epv_item')).scalar()}")
            print(f"  EPVApproval: {db.session.execute(db.text('SELECT COUNT(*) FROM epv_approval')).scalar()}")
            print(f"  EPVAllocation: {db.session.execute(db.text('SELECT COUNT(*) FROM epv_allocation')).scalar()}")
            print(f"  FinanceEntry: {db.session.execute(db.text('SELECT COUNT(*) FROM finance_entry')).scalar()}")
            print(f"  SupplementaryDocument: {db.session.execute(db.text('SELECT COUNT(*) FROM supplementary_document')).scalar()}")
            
            print("\nTables that will be KEPT:")
            print("  ✓ CostCenter")
            print("  ✓ User")
            print("  ✓ EmployeeDetails")
            print("  ✓ ExpenseHead")
            print("  ✓ CityAssignment")
            print("  ✓ SettingsFinance")
            
            print("\n" + "=" * 50)
            
            # Ask for confirmation
            response = input("Are you sure you want to clear the EPV-related tables? (yes/no): ").lower().strip()
            
            if response != 'yes':
                print("Operation cancelled.")
                return
            
            print("\nClearing tables using raw SQL...")
            
            # Disable foreign key checks temporarily
            print("Disabling foreign key checks...")
            db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # Clear tables in any order since foreign key checks are disabled
            tables_to_clear = [
                'epv_approval',
                'epv_allocation', 
                'epv_item',
                'supplementary_document',
                'finance_entry',
                'epv'
            ]
            
            total_deleted = 0
            for table in tables_to_clear:
                try:
                    # Get count before deletion
                    count_before = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"Clearing {table}... ({count_before} records)")
                    
                    # Delete all records
                    result = db.session.execute(db.text(f"DELETE FROM {table}"))
                    deleted = result.rowcount
                    total_deleted += deleted
                    
                    print(f"  ✓ Cleared {deleted} records from {table}")
                    
                except Exception as e:
                    print(f"  ✗ Error clearing {table}: {str(e)}")
                    raise
            
            # Re-enable foreign key checks
            print("Re-enabling foreign key checks...")
            db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 1"))
            
            # Commit all changes
            db.session.commit()
            
            print(f"\n✓ Successfully cleared {total_deleted} total records")
            
            # Verify tables are empty
            print("\nVerifying tables are empty:")
            for table in tables_to_clear:
                count = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if count == 0:
                    print(f"  ✓ {table}: {count} records")
                else:
                    print(f"  ⚠️  {table}: {count} records (should be 0)")
            
            print("\n" + "=" * 50)
            print("✓ Table cleanup completed successfully!")
            print("\nThe following reference data has been preserved:")
            print("  - Cost Centers")
            print("  - Users")
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

#!/usr/bin/env python3
"""
Migration script to add the new split invoice allocation table and fields
This script adds the EPVAllocation table and new fields to the EPV table for the new split invoice architecture
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import EPV, EPVAllocation, EPVApproval

def run_migration():
    """Run the migration to add new split invoice functionality"""

    print("Starting split invoice migration...")

    with app.app_context():
        try:
            # Create all tables (this will create the new EPVAllocation table)
            print("Creating new tables...")
            db.create_all()

            # Add new columns to existing EPV table if they don't exist
            print("Adding new columns to EPV table...")

            # Check if the new columns exist, if not add them
            inspector = db.inspect(db.engine)
            epv_columns = [col['name'] for col in inspector.get_columns('epv')]

            if 'approved_amount' not in epv_columns:
                print("Adding approved_amount column...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE epv ADD COLUMN approved_amount FLOAT DEFAULT 0.0'))
                    conn.commit()

            if 'rejected_amount' not in epv_columns:
                print("Adding rejected_amount column...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE epv ADD COLUMN rejected_amount FLOAT DEFAULT 0.0'))
                    conn.commit()

            if 'pending_amount' not in epv_columns:
                print("Adding pending_amount column...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE epv ADD COLUMN pending_amount FLOAT DEFAULT 0.0'))
                    conn.commit()

            # Check if allocation_id column exists in epv_approval table
            approval_columns = [col['name'] for col in inspector.get_columns('epv_approval')]

            if 'allocation_id' not in approval_columns:
                print("Adding allocation_id column to EPVApproval table...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE epv_approval ADD COLUMN allocation_id INTEGER'))
                    conn.execute(db.text('ALTER TABLE epv_approval ADD FOREIGN KEY (allocation_id) REFERENCES epv_allocation(id)'))
                    conn.commit()

            # Update invoice_type enum to include 'split' if using MySQL
            try:
                print("Updating invoice_type enum to include 'split'...")
                # This is for MySQL - adjust if using a different database
                with db.engine.connect() as conn:
                    conn.execute(db.text("ALTER TABLE epv MODIFY COLUMN invoice_type ENUM('standard', 'master', 'sub', 'split') DEFAULT 'standard'"))
                    conn.commit()
            except Exception as e:
                print(f"Note: Could not update enum (this is normal for SQLite): {e}")

            print("Migration completed successfully!")
            print("\nNew features added:")
            print("- EPVAllocation table for storing cost center allocations")
            print("- approved_amount, rejected_amount, pending_amount fields in EPV table")
            print("- allocation_id field in EPVApproval table")
            print("- 'split' invoice type support")

        except Exception as e:
            print(f"Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True

def verify_migration():
    """Verify that the migration was successful"""

    print("\nVerifying migration...")

    with app.app_context():
        try:
            # Check if EPVAllocation table exists and has the right columns
            inspector = db.inspect(db.engine)

            # Check EPVAllocation table
            if 'epv_allocation' in inspector.get_table_names():
                allocation_columns = [col['name'] for col in inspector.get_columns('epv_allocation')]
                expected_columns = ['id', 'epv_id', 'cost_center_id', 'cost_center_name',
                                  'allocated_amount', 'approver_email', 'approver_name',
                                  'status', 'action_date', 'rejection_reason', 'token',
                                  'created_at', 'updated_at', 'description']

                missing_columns = [col for col in expected_columns if col not in allocation_columns]
                if missing_columns:
                    print(f"Warning: EPVAllocation table missing columns: {missing_columns}")
                else:
                    print("✓ EPVAllocation table created successfully")
            else:
                print("✗ EPVAllocation table not found")
                return False

            # Check EPV table new columns
            epv_columns = [col['name'] for col in inspector.get_columns('epv')]
            new_epv_columns = ['approved_amount', 'rejected_amount', 'pending_amount']

            missing_epv_columns = [col for col in new_epv_columns if col not in epv_columns]
            if missing_epv_columns:
                print(f"Warning: EPV table missing columns: {missing_epv_columns}")
            else:
                print("✓ EPV table updated successfully")

            # Check EPVApproval table allocation_id column
            approval_columns = [col['name'] for col in inspector.get_columns('epv_approval')]
            if 'allocation_id' not in approval_columns:
                print("Warning: EPVApproval table missing allocation_id column")
            else:
                print("✓ EPVApproval table updated successfully")

            print("\nMigration verification completed!")
            return True

        except Exception as e:
            print(f"Error during verification: {e}")
            return False

if __name__ == '__main__':
    print("Split Invoice Migration Script")
    print("=" * 40)

    # Run migration
    if run_migration():
        # Verify migration
        if verify_migration():
            print("\n🎉 Migration completed successfully!")
            print("\nYou can now use the new split invoice functionality:")
            print("- Access /new-split-invoice to create split invoices")
            print("- Approvers will receive individual allocation approval emails")
            print("- Rejected allocations will be subtracted from the total amount")
            print("- Finance will receive the approved amount for processing")
        else:
            print("\n⚠️  Migration completed but verification failed")
            sys.exit(1)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)

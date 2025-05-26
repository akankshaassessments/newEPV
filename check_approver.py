#!/usr/bin/env python3
"""
Script to check if an email is set as an approver in the CostCenter table.
"""

from app import app, db
from models import CostCenter

def check_approver_email(email):
    """Check if an email is set as an approver in any active cost center."""
    with app.app_context():
        cost_centers = CostCenter.query.filter_by(approver_email=email).all()
        
        print(f"Found {len(cost_centers)} cost centers with approver email '{email}':")
        
        for cc in cost_centers:
            print(f"ID: {cc.id}, Name: {cc.costcenter}, Active: {cc.is_active}")
        
        active_cost_centers = CostCenter.query.filter_by(approver_email=email, is_active=True).all()
        print(f"\nFound {len(active_cost_centers)} ACTIVE cost centers with this approver.")

if __name__ == "__main__":
    # Check the specific email
    check_approver_email("3df.demo@akanksha.org")
    
    # Also list all approver emails for reference
    with app.app_context():
        all_approvers = db.session.query(CostCenter.approver_email).distinct().all()
        print("\nAll approver emails in the database:")
        for approver in all_approvers:
            if approver[0]:  # Check if not None
                print(f"- {approver[0]}")

from app import app, db
from models import CostCenter, EPV

def update_missing_cost_centers():
    with app.app_context():
        # Find the SBP_BP cost center in Pune
        sbp_bp = CostCenter.query.filter_by(costcenter='SBP_BP', city='Pune').first()
        
        if not sbp_bp:
            print("SBP_BP cost center not found in Pune")
            return
        
        # Get all master invoices without a cost center ID
        masters_without_cost_center = EPV.query.filter(
            EPV.invoice_type == 'master',
            (EPV.cost_center_id == None) | (EPV.cost_center_id == 0)
        ).all()
        
        print(f"Found {len(masters_without_cost_center)} master invoices without a cost center ID")
        
        # Update each master invoice
        for master in masters_without_cost_center:
            print(f"\nMaster invoice: {master.epv_id}")
            print(f"  Current cost center: {master.cost_center_name if master.cost_center_name else 'None'}")
            print(f"  Current cost center ID: {master.cost_center_id if master.cost_center_id else 'None'}")
            
            # Update the cost center
            master.cost_center_id = sbp_bp.id
            master.cost_center_name = sbp_bp.costcenter
            
            print(f"  Updated cost center to: {master.cost_center_name} (ID: {master.cost_center_id})")
        
        # Commit the changes
        db.session.commit()
        print(f"\nUpdated {len(masters_without_cost_center)} master invoices to use cost center {sbp_bp.costcenter}")

if __name__ == "__main__":
    update_missing_cost_centers()
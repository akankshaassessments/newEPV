from app import app, db
from models import CostCenter, EPV

def update_specific_master(epv_id):
    with app.app_context():
        # Find the master invoice
        master = EPV.query.filter_by(epv_id=epv_id).first()
        
        if not master:
            print(f"Master invoice {epv_id} not found")
            return
        
        print(f"Found master invoice: {master.epv_id}")
        print(f"Current cost center: {master.cost_center_name if master.cost_center_name else 'None'}")
        print(f"Current cost center ID: {master.cost_center_id if master.cost_center_id else 'None'}")
        
        # Find the SBP_BP cost center in Pune
        sbp_bp = CostCenter.query.filter_by(costcenter='SBP_BP', city='Pune').first()
        
        if not sbp_bp:
            print("SBP_BP cost center not found in Pune")
            return
        
        # Update the master invoice
        master.cost_center_id = sbp_bp.id
        master.cost_center_name = sbp_bp.costcenter
        
        # Commit the changes
        db.session.commit()
        
        print(f"Updated master invoice {master.epv_id} to use cost center {sbp_bp.costcenter}")

if __name__ == "__main__":
    # Get all master invoices to see which ones need updating
    with app.app_context():
        masters = EPV.query.filter_by(invoice_type='master').all()
        print("All master invoices:")
        for master in masters:
            print(f"ID: {master.id}, EPV ID: {master.epv_id}, Cost Center: {master.cost_center_name if master.cost_center_name else 'None'}")
        
        # Update any master that doesn't have SBP_BP as cost center
        sbp_bp = CostCenter.query.filter_by(costcenter='SBP_BP', city='Pune').first()
        if sbp_bp:
            updated_count = 0
            for master in masters:
                if master.cost_center_id != sbp_bp.id:
                    print(f"\nUpdating master invoice: {master.epv_id}")
                    print(f"  Current cost center: {master.cost_center_name if master.cost_center_name else 'None'}")
                    
                    # Update the master invoice
                    master.cost_center_id = sbp_bp.id
                    master.cost_center_name = sbp_bp.costcenter
                    updated_count += 1
            
            if updated_count > 0:
                # Commit the changes
                db.session.commit()
                print(f"\nUpdated {updated_count} master invoices to use cost center {sbp_bp.costcenter}")
            else:
                print("\nAll master invoices already using the correct cost center")
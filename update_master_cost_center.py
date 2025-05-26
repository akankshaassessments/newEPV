from app import app, db
from models import CostCenter, EPV

def update_master_invoices():
    with app.app_context():
        # Find a suitable cost center in Pune
        pune_centers = CostCenter.query.filter_by(city='Pune', is_active=True).all()
        
        if not pune_centers:
            print("No active cost centers found in Pune")
            return
        
        print("Available Pune cost centers:")
        for cc in pune_centers:
            print(f"ID: {cc.id}, Name: {cc.costcenter}, City: {cc.city}")
        
        # Use the first Pune cost center
        pune_cost_center = pune_centers[0]
        print(f"\nUsing cost center: {pune_cost_center.costcenter} (ID: {pune_cost_center.id})")
        
        # Get all master invoices
        master_invoices = EPV.query.filter_by(invoice_type='master').all()
        
        print(f"\nFound {len(master_invoices)} master invoices")
        
        # Update each master invoice
        updated_count = 0
        for master in master_invoices:
            print(f"\nMaster invoice: {master.epv_id}")
            print(f"  Current cost center: {master.cost_center_name if master.cost_center_name else 'None'}")
            print(f"  Current cost center ID: {master.cost_center_id if master.cost_center_id else 'None'}")
            
            # Update the cost center
            master.cost_center_id = pune_cost_center.id
            master.cost_center_name = pune_cost_center.costcenter
            updated_count += 1
            
            print(f"  Updated cost center to: {master.cost_center_name}")
        
        # Commit the changes
        db.session.commit()
        print(f"\nUpdated {updated_count} master invoices to use cost center {pune_cost_center.costcenter}")

if __name__ == "__main__":
    update_master_invoices()
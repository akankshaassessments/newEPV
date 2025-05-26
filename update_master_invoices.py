import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Motoming@123',
    'db': 'AFDW',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def update_master_invoices():
    """Update master invoices to set status to 'approved' if all sub-invoices are approved."""
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        
        with connection.cursor() as cursor:
            # Get all master invoices with split_status 'fully_approved'
            cursor.execute("""
                SELECT id, epv_id, status, split_status
                FROM epv
                WHERE invoice_type = 'master' AND split_status = 'fully_approved'
            """)
            
            master_invoices = cursor.fetchall()
            print(f"Found {len(master_invoices)} master invoices with split_status 'fully_approved'")
            
            for master in master_invoices:
                # Get all sub-invoices for this master
                cursor.execute("""
                    SELECT id, epv_id, status
                    FROM epv
                    WHERE master_invoice_id = %s
                """, (master['id'],))
                
                sub_invoices = cursor.fetchall()
                print(f"Master {master['epv_id']} has {len(sub_invoices)} sub-invoices")
                
                # Check if all sub-invoices are approved
                all_approved = True
                for sub in sub_invoices:
                    print(f"  Sub-invoice {sub['epv_id']} status: {sub['status']}")
                    if sub['status'] != 'approved':
                        all_approved = False
                        break
                
                # If all sub-invoices are approved, update the master invoice status
                if all_approved and len(sub_invoices) > 0:
                    if master['status'] != 'approved':
                        print(f"Updating master {master['epv_id']} status from '{master['status']}' to 'approved'")
                        cursor.execute("""
                            UPDATE epv
                            SET status = 'approved'
                            WHERE id = %s
                        """, (master['id'],))
                        connection.commit()
                    else:
                        print(f"Master {master['epv_id']} already has status 'approved'")
                else:
                    print(f"Not all sub-invoices for master {master['epv_id']} are approved")
            
            print("Master invoice update completed")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        connection.close()

if __name__ == "__main__":
    update_master_invoices()
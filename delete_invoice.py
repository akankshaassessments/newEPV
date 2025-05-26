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

def delete_master_invoice(epv_id):
    """Delete a master invoice and all its sub-invoices."""
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        
        with connection.cursor() as cursor:
            # Find the master invoice
            cursor.execute(
                "SELECT id, epv_id FROM epv WHERE epv_id = %s",
                (epv_id,)
            )
            master = cursor.fetchone()
            
            if not master:
                print(f"Master invoice {epv_id} not found")
                return
            
            print(f"Found master invoice: ID={master['id']}, EPV ID={master['epv_id']}")
            
            # Find all sub-invoices
            cursor.execute(
                "SELECT id, epv_id FROM epv WHERE master_invoice_id = %s",
                (master['id'],)
            )
            sub_invoices = cursor.fetchall()
            
            print(f"Found {len(sub_invoices)} sub-invoices:")
            for sub in sub_invoices:
                print(f"  ID={sub['id']}, EPV ID={sub['epv_id']}")
            
            # Delete all related records in dependent tables
            
            # 1. Delete approvals for sub-invoices
            for sub in sub_invoices:
                cursor.execute(
                    "DELETE FROM epv_approval WHERE epv_id = %s",
                    (sub['id'],)
                )
                print(f"Deleted approvals for sub-invoice {sub['epv_id']}")
                
                # Delete EPV items for sub-invoices
                cursor.execute(
                    "DELETE FROM epv_item WHERE epv_id = %s",
                    (sub['id'],)
                )
                print(f"Deleted items for sub-invoice {sub['epv_id']}")
            
            # 2. Delete approvals for master invoice
            cursor.execute(
                "DELETE FROM epv_approval WHERE epv_id = %s",
                (master['id'],)
            )
            print(f"Deleted approvals for master invoice {master['epv_id']}")
            
            # 3. Delete EPV items for master invoice
            cursor.execute(
                "DELETE FROM epv_item WHERE epv_id = %s",
                (master['id'],)
            )
            print(f"Deleted items for master invoice {master['epv_id']}")
            
            # 4. Delete finance entries for master invoice
            cursor.execute(
                "DELETE FROM finance_entry WHERE epv_id = %s",
                (master['id'],)
            )
            print(f"Deleted finance entries for master invoice {master['epv_id']}")
            
            # 5. Delete sub-invoices
            for sub in sub_invoices:
                cursor.execute(
                    "DELETE FROM epv WHERE id = %s",
                    (sub['id'],)
                )
                print(f"Deleted sub-invoice {sub['epv_id']}")
            
            # 6. Delete master invoice
            cursor.execute(
                "DELETE FROM epv WHERE id = %s",
                (master['id'],)
            )
            print(f"Deleted master invoice {master['epv_id']}")
            
            # Commit the transaction
            connection.commit()
            print("All deletions committed successfully")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        connection.rollback()
        print("All changes rolled back due to error")
    finally:
        connection.close()

if __name__ == "__main__":
    epv_id = "EPV-20250414-SPLIT4E15"
    delete_master_invoice(epv_id)
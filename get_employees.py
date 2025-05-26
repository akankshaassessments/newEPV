from models import db, EmployeeDetails
import pymysql

print('Available employee names:')
for employee in EmployeeDetails.query.all():
    print(f'{employee.email} -> {employee.name}')

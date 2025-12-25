# File: fix_db.py
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')
django.setup()

from django.db import connection

def fix_database():
    cursor = connection.cursor()
    
    print("Checking database...")
    
    # Check all project-related tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'projects_%';")
    tables = cursor.fetchall()
    print(f"Project tables: {tables}")
    
    # Check SupervisorMeeting table specifically
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects_supervisormeeting';")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print("\nFound projects_supervisormeeting table")
        
        # Count rows
        cursor.execute("SELECT COUNT(*) FROM projects_supervisormeeting;")
        count = cursor.fetchone()[0]
        print(f"Rows in table: {count}")
        
        if count > 0:
            print("Deleting all rows...")
            cursor.execute("DELETE FROM projects_supervisormeeting;")
            connection.commit()
            print(f"Deleted {count} rows")
        else:
            print("Table is empty")
    else:
        print("\nNo projects_supervisormeeting table found")
    
    cursor.close()
    print("\nDatabase fixed. Now try running migrations.")

if __name__ == "__main__":
    fix_database()
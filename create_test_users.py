# create_test_users.py
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')
django.setup()

from accounts.models import User

def create_test_users():
    print("Creating test users...")
    
    # Test Student 1
    try:
        student1 = User.objects.create_user(
            username='Sanjay',
            email='sanjay@gmail.com',
            password='sanjay0713',
            role='student',
            full_name='Sanjay Nepali',
            user_id='STU1',
            is_enabled=True
        )
        print("✅ Student 1 created: Sanjay")
    except Exception as e:
        print(f"❌ Error creating student 1: {e}")

    # Test Student 2
    try:
        student2 = User.objects.create_user(
            username='Nupur',
            email='nupur@gmail.com',
            password='sanjay0713',
            role='student',
            full_name='Nupur Sharma',
            user_id='STU2',
            is_enabled=True
        )
        print("✅ Student 2 created: Nupur")
    except Exception as e:
        print(f"❌ Error creating student 2: {e}")

    # Test Supervisor
    try:
        supervisor = User.objects.create_user(
            username='Dipak', 
            email='dipak@gmail.com',
            password='sanjay0713',
            role='supervisor',
            full_name='Dipak Dahal',
            user_id='SUP1',
            is_enabled=True
        )
        print("✅ Supervisor created: Dipak")
    except Exception as e:
        print(f"❌ Error creating supervisor: {e}")

    # Test Admin
    try:
        admin = User.objects.create_user(
            username='admin',
            email='admin@gmail.com', 
            password='sanjay0713',
            role='admin',
            full_name='Admin',
            user_id='ADM1',
            is_enabled=True
        )
        print("✅ Admin created: Admin")
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
    
    print("\n" + "="*50)
    print("TEST USERS CREATED SUCCESSFULLY!")
    print("="*50)
    print("Student 1: sanjay@gmail.com / sanjay0713")
    print("Student 2: nupur@gmail.com / sanjay0713")
    print("Supervisor: dipak@gmail.com / sanjay0713") 
    print("Admin: admin@gmail.com / sanjay0713")
    print("\nLogin URL: http://127.0.0.1:8000/accounts/login/")
    print("="*50)

if __name__ == "__main__":
    create_test_users()
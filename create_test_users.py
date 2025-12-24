# create_test_users.py - UPDATED VERSION
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')
django.setup()

from accounts.models import User
from django.utils import timezone

def create_test_users():
    print("Creating test users for batch 2079...")
    
    # Set common batch year
    BATCH_YEAR = 2079
    
    # List of 15 students
    students = [
        {"username": "Sanjay", "full_name": "Sanjay Nepali", "email": "sanjay@gmail.com"},
        {"username": "Nupur", "full_name": "Nupur Sharma", "email": "nupur@gmail.com"},
        {"username": "Rajesh", "full_name": "Rajesh Yadav", "email": "rajesh@gmail.com"},
        {"username": "Sita", "full_name": "Sita Karki", "email": "sita@gmail.com"},
        {"username": "Ram", "full_name": "Ram Bahadur", "email": "ram@gmail.com"},
        {"username": "Gita", "full_name": "Gita Thapa", "email": "gita@gmail.com"},
        {"username": "Hari", "full_name": "Hari Prasad", "email": "hari@gmail.com"},
        {"username": "Sabina", "full_name": "Sabina Rai", "email": "sabina@gmail.com"},
        {"username": "Krishna", "full_name": "Krishna Shrestha", "email": "krishna@gmail.com"},
        {"username": "Anita", "full_name": "Anita Gurung", "email": "anita@gmail.com"},
        {"username": "Bikash", "full_name": "Bikash Tamang", "email": "bikash@gmail.com"},
        {"username": "Puja", "full_name": "Puja Limbu", "email": "puja@gmail.com"},
        {"username": "Suresh", "full_name": "Suresh Magar", "email": "suresh@gmail.com"},
        {"username": "Mina", "full_name": "Mina Thakuri", "email": "mina@gmail.com"},
        {"username": "Dipesh", "full_name": "Dipesh Basnet", "email": "dipesh@gmail.com"}
    ]
    
    # Create 15 students with batch 2079 and bypass password change
    print(f"\n👨‍🎓 CREATING 15 STUDENTS (Batch {BATCH_YEAR}):")
    print("-" * 50)
    
    for i, student in enumerate(students, 1):
        try:
            # Check if user already exists
            if User.objects.filter(username=student["username"]).exists():
                print(f"⚠️  Skipping existing student: {student['username']}")
                continue
                
            user = User.objects.create_user(
                username=student["username"],
                email=student["email"],
                password='student123',  # Same password for all students
                role='student',
                full_name=student["full_name"],
                user_id=f'STU{i:03d}',
                batch_year=BATCH_YEAR,
                # CRITICAL: Bypass password change requirement
                password_changed=True,
                must_change_password=False,
                initial_password_visible=False,
                password_changed_at=timezone.now(),
                is_enabled=True
            )
            print(f"✅ Student {i:2d}: {student['username']} - {student['full_name']} (Batch {BATCH_YEAR})")
        except Exception as e:
            print(f"❌ Error creating student {student['username']}: {e}")
    
    print("\n" + "="*50)
    
    # Create 3 supervisors with batch 2079
    supervisors = [
        {"username": "Dipak", "full_name": "Dipak Dahal", "email": "dipak@gmail.com"},
        {"username": "Binod", "full_name": "Binod Poudel", "email": "binod@gmail.com"},
        {"username": "Rita", "full_name": "Rita Sharma", "email": "rita@gmail.com"}
    ]
    
    print(f"\n👨‍🏫 CREATING 3 SUPERVISORS (Batch {BATCH_YEAR}):")
    print("-" * 50)
    
    for i, supervisor in enumerate(supervisors, 1):
        try:
            # Check if user already exists
            if User.objects.filter(username=supervisor["username"]).exists():
                print(f"⚠️  Skipping existing supervisor: {supervisor['username']}")
                continue
                
            User.objects.create_user(
                username=supervisor["username"],
                email=supervisor["email"],
                password='supervisor123',  # Same password for all supervisors
                role='supervisor',
                full_name=supervisor["full_name"],
                user_id=f'SUP{i:02d}',
                batch_year=BATCH_YEAR,
                # CRITICAL: Bypass password change requirement
                password_changed=True,
                must_change_password=False,
                initial_password_visible=False,
                password_changed_at=timezone.now(),
                is_enabled=True
            )
            print(f"✅ Supervisor {i}: {supervisor['username']} - {supervisor['full_name']} (Batch {BATCH_YEAR})")
        except Exception as e:
            print(f"❌ Error creating supervisor {supervisor['username']}: {e}")
    
    print("\n" + "="*50)
    
    # Create 1 admin
    print("\n👑 CREATING ADMIN:")
    print("-" * 50)
    
    try:
        # Check if admin already exists
        if User.objects.filter(username='admin').exists():
            print("⚠️  Admin user already exists, updating...")
            admin = User.objects.get(username='admin')
            admin.batch_year = BATCH_YEAR
            admin.password_changed = True
            admin.must_change_password = False
            admin.initial_password_visible = False
            admin.password_changed_at = timezone.now()
            admin.is_enabled = True
            admin.save()
            print("✅ Admin updated")
        else:
            admin = User.objects.create_user(
                username='admin',
                email='admin@gmail.com', 
                password='admin123',
                role='admin',
                full_name='Admin',
                user_id='ADM001',
                batch_year=BATCH_YEAR,
                # CRITICAL: Bypass password change requirement
                password_changed=True,
                must_change_password=False,
                initial_password_visible=False,
                password_changed_at=timezone.now(),
                is_enabled=True
            )
            print("✅ Admin created")
    except Exception as e:
        print(f"❌ Error creating/updating admin: {e}")
    
    print("\n" + "="*50)
    print("✅ TEST USERS CREATED/VERIFIED SUCCESSFULLY!")
    print("="*50)
    
    # Statistics
    total_students = User.objects.filter(role='student', batch_year=BATCH_YEAR).count()
    total_supervisors = User.objects.filter(role='supervisor', batch_year=BATCH_YEAR).count()
    total_admins = User.objects.filter(role='admin', batch_year=BATCH_YEAR).count()
    
    print(f"\n📊 BATCH {BATCH_YEAR} STATISTICS:")
    print("-" * 30)
    print(f"Students:      {total_students}/15")
    print(f"Supervisors:   {total_supervisors}/3")
    print(f"Admins:        {total_admins}/1")
    
    print("\n🔓 LOGIN CREDENTIALS (Password Change Bypassed):")
    print("="*50)
    print("\n👨‍🎓 STUDENTS (15 users):")
    print("-" * 30)
    print("Email: username@gmail.com")
    print("Password: student123")
    print("Example: sanjay@gmail.com / student123")
    print("Status: Password already changed ✅")
    
    print("\n👨‍🏫 SUPERVISORS (3 users):")
    print("-" * 30)
    print("Email: username@gmail.com")
    print("Password: supervisor123")
    print("Example: dipak@gmail.com / supervisor123")
    print("Status: Password already changed ✅")
    
    print("\n👑 ADMIN (1 user):")
    print("-" * 30)
    print("Email: admin@gmail.com")
    print("Password: admin123")
    print("Status: Password already changed ✅")
    
    print("\n⚠️  IMPORTANT: All users bypass initial password change!")
    print("   They can login directly without changing password.")
    
    print("\n🌐 LOGIN URL:")
    print("-" * 30)
    print("http://127.0.0.1:8000/accounts/login/")
    print("="*50)
    
    # Verify all users have password_changed=True
    print("\n🔍 VERIFICATION:")
    print("-" * 30)
    
    users_need_password_change = User.objects.filter(
        must_change_password=True,
        is_enabled=True
    ).exclude(is_superuser=True).count()
    
    if users_need_password_change == 0:
        print("✅ All users bypass password change requirement")
    else:
        print(f"⚠️  {users_need_password_change} users still need password change")
        
    batch_users = User.objects.filter(batch_year=BATCH_YEAR).count()
    print(f"✅ {batch_users} users in batch {BATCH_YEAR}")

if __name__ == "__main__":
    create_test_users()
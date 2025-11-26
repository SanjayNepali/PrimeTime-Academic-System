# File: Desktop/Prime/populate_university_db.py

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')
django.setup()

from accounts.models import UniversityDatabase

# Sample data for testing
university_data = [
    {
        'user_id': 'STU2025001',
        'full_name': 'Sanjay Nepali',
        'email': 'sanjay.nepali@university.edu',
        'department': 'Computer Science',
        'role': 'student',
        'enrollment_year': 2022,
        'phone': '+9779763588537'
    },
    {
        'user_id': 'STU2025002',
        'full_name': 'Nupur Sharma',
        'email': 'nupur.sharma@university.edu',
        'department': 'Computer Science',
        'role': 'student',
        'enrollment_year': 2022,
        'phone': '+9779863778427'
    },
    {
        'user_id': 'SUP2020001',
        'full_name': 'Dipak Dahal',
        'email': 'dipak.dahal@university.edu',
        'department': 'Computer Science',
        'role': 'supervisor',
        'enrollment_year': None,
        'phone': '+9779862403190'
    }
]

for data in university_data:
    UniversityDatabase.objects.get_or_create(
        user_id=data['user_id'],
        defaults=data
    )

print("University database populated with sample data")
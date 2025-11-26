#!/usr/bin/env python
"""Check all registered admin models"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_system.settings')
django.setup()

from django.contrib import admin

print('=' * 60)
print('REGISTERED MODELS IN DJANGO ADMIN')
print('=' * 60)

apps_models = {}
for model, admin_class in admin.site._registry.items():
    app_label = model._meta.app_label
    if app_label not in apps_models:
        apps_models[app_label] = []
    apps_models[app_label].append({
        'model': model.__name__,
        'admin': admin_class.__class__.__name__
    })

for app_name in sorted(apps_models.keys()):
    print(f'\n{app_name.upper()}:')
    for item in apps_models[app_name]:
        print(f"  - {item['model']:30s} -> {item['admin']}")

print('\n' + '=' * 60)
print(f'Total: {len(admin.site._registry)} models registered')
print('=' * 60)

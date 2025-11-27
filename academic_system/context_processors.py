# File: Desktop/Prime/academic_system/context_processors.py

def user_permissions(request):
    """
    Context processor to provide consistent admin permission checks
    """
    user = request.user
    
    if not user.is_authenticated:
        return {
            'is_admin_user': False,
            'is_superuser': False,
        }
    
    # Comprehensive admin check - superusers are always admins
    is_admin_user = any([
        user.is_superuser,  # Superusers are always admins
        getattr(user, 'is_admin', False),  # Custom is_admin property
        getattr(user, 'role', None) in ['admin', 'superadmin']  # Role-based admin
    ])
    
    return {
        'is_admin_user': is_admin_user,
        'is_superuser': user.is_superuser,
    }
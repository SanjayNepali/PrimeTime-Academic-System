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
        user.is_superuser,
        getattr(user, 'is_admin', False),
        getattr(user, 'role', None) == 'admin'
    ])
    
    return {
        'is_admin_user': is_admin_user,
        'is_superuser': user.is_superuser,
    }
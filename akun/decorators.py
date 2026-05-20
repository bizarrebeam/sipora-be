"""
Role-Based Access Control (RBAC) Decorators for Django REST Framework Views.

This module provides method-level authorization decorators that enforce role-based
access restrictions on API endpoints. The 'kemahasiswaan' role is treated as a
super-administrator with implicit access to all protected resources.
"""

from rest_framework.response import Response
from functools import wraps

def role_required(*roles):
    """
    Restricts access to a view method based on the authenticated user's role.

    The 'kemahasiswaan' role always bypasses the check (super-admin access).
    If the user's role is not in the allowed list, a 404 response is returned
    (intentionally obscures the existence of the endpoint from unauthorized users).

    Usage:
        @role_required('guru_bk', 'kemahasiswaan')
        def get(self, request):
            ...

    Args:
        *roles: One or more role strings that are permitted to access the endpoint.

    Returns:
        A decorator that wraps the view method with role validation.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(view_instance, request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response({"detail": "Autentikasi diperlukan."}, status=401)
            
            if request.user.role == 'kemahasiswaan':
                return view_func(view_instance, request, *args, **kwargs)

            if request.user.role not in roles:
                return Response({"detail": "Tidak ditemukan."}, status=404)
            
            return view_func(view_instance, request, *args, **kwargs)
        return _wrapped_view
    return decorator

    
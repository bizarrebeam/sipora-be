from rest_framework.response import Response
from functools import wraps

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(view_instance, request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response({"detail": "Autentikasi diperlukan."}, status=401)
            
            if request.user.role == 'kemahasiswaan':
                return view_func(view_instance, request, *args, **kwargs)

            if request.user.role not in roles:
                return Response({"detail": "Anda tidak memiliki akses untuk melakukan aksi ini."}, status=403)
            
            return view_func(view_instance, request, *args, **kwargs)
        return _wrapped_view
    return decorator
"""
Custom Authentication Mechanics for the Django REST Framework.

This module extends the SimpleJWT authentication protocol to seamlessly support
HTTP-Only Cookie-based token delivery, mitigating XSS vulnerability vectors.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication backend that attempts to extract the access token
    from HTTP-Only cookies if the standard Authorization header is absent.
    """
    def authenticate(self, request):
        """
        Interrogates the incoming request for a valid JWT.
        Prioritizes the Authorization header, falling back to the configured
        authentication cookie.
        """
        header = self.get_header(request)

        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            cookie_name = getattr(settings, 'AUTH_COOKIE', 'access_token')
            raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            return None

        if isinstance(raw_token, str):
            raw_token = raw_token.encode('utf-8')

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except (AuthenticationFailed, InvalidToken):
            return None

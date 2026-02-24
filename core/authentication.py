from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from rest_framework_simplejwt.exceptions import AuthenticationFailed

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
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

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

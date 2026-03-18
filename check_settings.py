import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sipora_be.settings')
django.setup()

print(f'EMAIL_PORT: {settings.EMAIL_PORT}')
print(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
print(f'EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}')
print(f'EMAIL_TIMEOUT: {settings.EMAIL_TIMEOUT}')

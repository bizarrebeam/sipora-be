import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sipora_be.settings')
django.setup()

print(f'EMAIL_PORT: {settings.EMAIL_PORT}')
print(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
print(f'EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}')
print(f'EMAIL_TIMEOUT: {settings.EMAIL_TIMEOUT}')

import socket
print(f"\n--- Diagnostic: Testing Connection to {settings.EMAIL_HOST}:{settings.EMAIL_PORT} ---")
try:
    sock = socket.create_connection((settings.EMAIL_HOST, settings.EMAIL_PORT), timeout=settings.EMAIL_TIMEOUT)
    print(f"SUCCESS: Successfully connected to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    sock.close()
except Exception as e:
    print(f"FAILURE: Could not connect to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    print(f"Error: {str(e)}")

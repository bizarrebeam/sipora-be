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
print(f"\n--- Diagnostic: DNS Resolution for {settings.EMAIL_HOST} ---")
try:
    info = socket.getaddrinfo(settings.EMAIL_HOST, settings.EMAIL_PORT)
    for res in info:
        family = "IPv4" if res[0] == socket.AF_INET else "IPv6"
        print(f"Found {family} address: {res[4][0]}")
except Exception as e:
    print(f"DNS Resolution Failed: {str(e)}")

print(f"\n--- Diagnostic: Testing Connection (Default) ---")
try:
    sock = socket.create_connection((settings.EMAIL_HOST, settings.EMAIL_PORT), timeout=settings.EMAIL_TIMEOUT)
    print(f"SUCCESS: Connected to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    sock.close()
except Exception as e:
    print(f"FAILURE (Default): {str(e)}")

print(f"\n--- Diagnostic: Testing Connection (FORCED IPv4) ---")
try:
    # Get IPv4 addresses only
    ipv4_info = socket.getaddrinfo(settings.EMAIL_HOST, settings.EMAIL_PORT, socket.AF_INET, socket.SOCK_STREAM)
    if not ipv4_info:
        print("No IPv4 addresses found for host.")
    else:
        target_ip = ipv4_info[0][4][0]
        print(f"Attempting connection to {target_ip}:{settings.EMAIL_PORT}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(settings.EMAIL_TIMEOUT)
        sock.connect((target_ip, settings.EMAIL_PORT))
        print(f"SUCCESS (IPv4): Connected to {target_ip}:{settings.EMAIL_PORT}")
        sock.close()
except Exception as e:
    print(f"FAILURE (IPv4): {str(e)}")

import os
import requests
from django.core.mail.backends.base import BaseEmailBackend

import logging

logger = logging.getLogger(__name__)


class VercelProxyEmailBackend(BaseEmailBackend):
    """
    A custom email backend that proxies email requests to a Serverless Function.
    Used for centralized email dispatching through HTTP.
    """
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
            
        sent_counter = 0
        
        frontend_url = os.getenv("FRONTEND_URL", "https://sipora-fe.vercel.app").rstrip("/")
        if not frontend_url.startswith("http"):
            frontend_url = "https://sipora-fe.vercel.app"
            
        vercel_url = f"{frontend_url}/api/send-email"
        secret = os.getenv("VERCEL_EMAIL_SECRET", "supersekret")
        
        for message in email_messages:
            is_html = False
            html_content = ""
            
            if hasattr(message, 'alternatives') and message.alternatives:
                for alt_content, alt_type in message.alternatives:
                    if alt_type == 'text/html':
                        html_content = alt_content
                        is_html = True
                        break
            
            if not is_html:
                html_content = message.body
                
            payload = {
                "secret": secret,
                "to": message.to[0] if message.to else "",
                "subject": message.subject,
                "html": html_content
            }
            
            try:
                response = requests.post(vercel_url, json=payload, timeout=15)
                if response.status_code == 200:
                    sent_counter += 1
                else:
                    logger.error(f"[Vercel Proxy Error {response.status_code}]: {response.text}")
                    if not self.fail_silently:
                        response.raise_for_status()
            except Exception as e:
                logger.error(f"[Email Proxy Exception]: Failed to contact {vercel_url} -> {e}")
                if not self.fail_silently:
                    raise e
                    
        return sent_counter

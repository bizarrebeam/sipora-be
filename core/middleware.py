"""
Custom Middleware Definitions for the Django Application.

This module houses HTTP request/response pipeline interceptors utilized for
monitoring, telemetry, and debugging.
"""

import time
import logging

logger = logging.getLogger('django.request')


class TimingMiddleware:
    """
    Diagnostic middleware that logs the isolated server-side execution duration
    of incoming HTTP requests (excluding network latency bottlenecks).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start
        ms = duration * 1000
        print(f"[TIMING] {request.method} {request.path} -> {response.status_code} ({ms:.0f}ms)")
        return response

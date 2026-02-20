import time
import logging

logger = logging.getLogger('django.request')


class TimingMiddleware:
    """Logs how long each request takes inside Django (excludes network)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start
        ms = duration * 1000
        print(f"[TIMING] {request.method} {request.path} -> {response.status_code} ({ms:.0f}ms)")
        return response

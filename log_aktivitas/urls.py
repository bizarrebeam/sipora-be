"""
URL Routing for Activity Logging.

Registers the REST endpoint providing access to the paginated administrative audit trail.
"""

from django.urls import path
from .views import DaftarLogView

urlpatterns = [
    path('', DaftarLogView.as_view()),
]
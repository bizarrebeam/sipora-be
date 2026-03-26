"""
Abstract Base Models and Object Managers for the Core Application.

This module defines ubiquitous architectural patterns, such as the Soft Delete
mechanism, intended for inheritance by domain-specific models throughout the system.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone

class ActiveManager(models.Manager):
    """
    Custom QuerySet manager that exclusively retrieves active, non-soft-deleted entries.
    Overrides the default query behavior to hide logically deleted records from the application layer.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """
    Abstract Base Model implementing the logical deletion pattern.
    Entities inheriting this class will not be permanently purged from the physical database
    upon invoking delete(). Instead, their state transitions to 'is_deleted=True' to maintain systemic audit trails.
    """
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='+'
    )

    # Base query manager restricted to active records.
    objects = ActiveManager()
    
    # Unrestricted query manager providing access to all records, including deleted ones.
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """
        Flags the model instance as deleted and records the timestamp and acting entity.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()

    def delete(self, *args, **kwargs):
        """
        Intercepts the standard physical deletion procedure and enforces a soft delete instead.
        """
        self.soft_delete()

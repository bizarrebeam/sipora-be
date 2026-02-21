from django.db import models
from django.conf import settings
from django.utils import timezone

class ActiveManager(models.Manager):
    """
    Manager to only return objects that have not been soft-deleted.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """
    Abstract Base Class for implementing Soft Delete.
    All models inheriting from this will not be hard-deleted from the database unless forced.
    Instead, they are marked with is_deleted=True to preserve audit trails.
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

    # Managers
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()

    def delete(self, *args, **kwargs):
        """
        Prevent hard deletion by overriding the default delete method.
        Automatically converts to soft_delete.
        """
        self.soft_delete()

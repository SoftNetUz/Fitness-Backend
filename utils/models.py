from django.db import models
from django.conf import settings

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)s_set"
        )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)s_set"
    )
    state = models.BooleanField(default=True)

    class Meta:
        abstract = True
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder

class BaseManager(models.Manager):
    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at=None)


class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True


class BaseModelMixin(TimestampMixin):
    meta    = models.JSONField(default=dict, blank=True, null=True, encoder=DjangoJSONEncoder)
    objects = BaseManager()

    class Meta:
        abstract = True
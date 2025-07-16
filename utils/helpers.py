import random, secrets, string

from django.db import models
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder


def random_alphanumeric(length=8):

    characters = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string


class BaseManager(models.Manager):
    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at=None)

    def all_objects(self):
        return super().get_queryset()


class TimestampMixin(models.Model):
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Soft delete the object by setting `deleted_at` to the current time."""
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore a soft-deleted object by setting `deleted_at` to None."""
        self.deleted_at = None
        self.save()


class BaseModelMixin(TimestampMixin):
    # meta = models.JSONField(default=dict, blank=True, null=True, encoder=DjangoJSONEncoder)
    objects = BaseManager()  

    class Meta:
        abstract = True

def random_alphanumeric(length=8):

    characters = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string
import uuid
from django.db import models
from django.conf import settings


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="events",
    )

    source = models.CharField(max_length=128)
    event_type = models.CharField(max_length=128)

    timestamp = models.DateTimeField()

    payload = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.id}"

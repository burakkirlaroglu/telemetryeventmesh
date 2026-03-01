import uuid
from django.db import models
from django.conf import settings
from django.db.models.enums import TextChoices


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

    def __str__(self):
        return f"{self.event_type} - {self.id}"


class StatusEnum(TextChoices):
    ACCEPTED = "accepted", "Accepted"
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    OVER = "over", "Over"


class ProcessingState(models.Model):
    event = models.OneToOneField(
        "Event",
        on_delete=models.CASCADE,
        related_name="processing_state",
    )

    status = models.CharField(
        max_length=32,
        choices=StatusEnum.choices,
        default=StatusEnum.ACCEPTED,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    locked_at = models.DateTimeField(null=True, blank=True)
    worker_id = models.CharField(max_length=64, null=True, blank=True)

    retry_count = models.PositiveIntegerField(default=0)

    last_error = models.TextField(
        null=True,
        blank=True,
    )

    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["status"], name="idx_processing_status"),
            models.Index(fields=["next_retry_at"], name="idx_retry_schedule"),
        ]

    def __str__(self):
        return f"{self.event_id} - {self.status}"


class ProcessedEventLog(models.Model):
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="processed_log",
    )

    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_id} processed"

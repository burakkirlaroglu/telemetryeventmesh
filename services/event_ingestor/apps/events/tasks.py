from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import ProcessingState, StatusEnum


@shared_task(bind=True, acks_late=True)
def process_events_batch(self, batch_size=10):
    processed_count = 0
    while True:
        with transaction.atomic():
            states = (
                ProcessingState.objects
                .select_for_update(skip_locked=True)
                .select_related("event")
                .filter(status=StatusEnum.QUEUED)
                .order_by("created_at")[:batch_size]
            )

            if not states:
                break

            for state in states:
                state.status = StatusEnum.PROCESSING
                state.worker_id = self.request.hostname
                state.locked_at = timezone.now()
                state.save(update_fields=["status", "worker_id", "locked_at", "updated_at"])

        # out of atomic transaction process
        for state in states:
            try:
                # todo: real process logic
                state.status = StatusEnum.PROCESSED
                state.save(update_fields=["status", "updated_at"])
                processed_count += 1
            except Exception:
                state.status = StatusEnum.FAILED
                state.save(update_fields=["status", "updated_at"])

    return processed_count

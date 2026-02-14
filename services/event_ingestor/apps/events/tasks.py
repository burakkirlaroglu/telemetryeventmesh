from celery import shared_task
from django.db import transaction

from .models import ProcessingState, StatusEnum


@shared_task
def process_events_batch(batch_size=10):
    # todo: real processing later
    with transaction.atomic():
        states = (
            ProcessingState.objects
            .select_for_update(skip_locked=True)
            .select_related("event")
            .filter(status=StatusEnum.ACCEPTED)[:batch_size]
        )

        for state in states:
            state.status = StatusEnum.PROCESSING
            state.worker_id = "worker-1"
            state.save(update_fields=["status", "worker_id", "updated_at"])

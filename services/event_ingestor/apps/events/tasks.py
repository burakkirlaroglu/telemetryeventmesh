from django.utils import timezone
from datetime import timedelta
from celery import shared_task
from django.db import transaction, IntegrityError
import redis
from django.conf import settings

from .models import ProcessingState, StatusEnum, ProcessedEventLog
import logging
import json

logger = logging.getLogger(__name__)


@shared_task(bind=True, queue="processing_queue", acks_late=True)
def process_events_batch(self, batch_size=10):
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
    )

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
                ProcessedEventLog.objects.create(event=state.event)
                state.status = StatusEnum.PROCESSED
                state.save(update_fields=["status", "updated_at"])
                processed_count += 1
                now = timezone.now()
                duration_ms = None

                if state.locked_at:
                    duration_ms = int((now - state.locked_at).total_seconds() * 1000)

                logger.info(json.dumps({
                    "type": "event.process.succeeded",
                    "event_id": str(state.event_id),
                    "worker_id": state.worker_id,
                    "duration_ms": duration_ms,
                    "status_from": "processing",
                    "status_to": "processed",
                }))

                payload = {
                    "type": "event.update",
                    "event_id": str(state.event_id),
                    "status": state.status,
                }

                r.publish("tem:events", json.dumps(payload))


            except IntegrityError:
                # Event already processed - db level Idempotency
                state.status = StatusEnum.PROCESSED
                state.save(update_fields=["status", "updated_at"])

                logger.warning(json.dumps({
                    "type": "event.process.idempotency_conflict",
                    "event_id": str(state.event_id),
                }))

                payload = {
                    "type": "event.update",
                    "event_id": str(state.event_id),
                    "status": state.status,
                }

                r.publish("tem:events", json.dumps(payload))


            except Exception:
                state.status = StatusEnum.FAILED
                state.save(update_fields=["status", "updated_at"])

                logger.error(json.dumps({
                    "type": "event.process.failed",
                    "event_id": str(state.event_id),
                    "worker_id": state.worker_id,
                    "status": "failed",
                }))

    return processed_count


@shared_task(queue="maintenance_queue")
def recover_stuck_processing(timeout_seconds=60, batch_size=50):
    threshold = timezone.now() - timedelta(seconds=timeout_seconds)

    recovered = 0

    with transaction.atomic():
        stuck_states = (
            ProcessingState.objects
            .select_for_update(skip_locked=True)
            .filter(
                status=StatusEnum.PROCESSING,
                locked_at__lt=threshold
            )
            .order_by("locked_at")[:batch_size]
        )

        for state in stuck_states:
            state.status = StatusEnum.QUEUED
            state.worker_id = None
            state.locked_at = None
            state.save(update_fields=["status", "worker_id", "locked_at", "updated_at"])
            recovered += 1

    logger.warning(json.dumps({
        "type": "event.process.recovered",
        "requeued_count": recovered,
    }))

    return recovered

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import User, APIKey
from apps.events.models import (
    Event,
    ProcessingState,
    StatusEnum,
    ProcessedEventLog,
)
from apps.events.tasks import recover_stuck_processing


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class EventProcessingTest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser",
            password="testpass",
            role="admin",
        )

        cls.api_key = APIKey.objects.create(
            user=cls.user,
            key="test-api-key",
        )

        cls.url = reverse("event-ingest")

    def _valid_payload(self):
        return {
            "source": "payment-api",
            "event_type": "payment.success",
            "timestamp": timezone.now().isoformat(),
            "payload": {
                "order_id": "12345",
                "amount": 150.0,
            },
        }

    def test_event_creates_processing_state(self):
        response = self.client.post(
            self.url,
            self._valid_payload(),
            format="json",
            HTTP_X_API_KEY="test-api-key",
        )

        self.assertEqual(response.status_code, 202)

        event = Event.objects.get()
        state = ProcessingState.objects.get(event=event)

        self.assertEqual(state.status, StatusEnum.PROCESSED)

    def test_idempotency_prevents_duplicate_processing(self):
        self.client.post(
            self.url,
            self._valid_payload(),
            format="json",
            HTTP_X_API_KEY="test-api-key",
        )

        event = Event.objects.get()

        from apps.events.tasks import process_events_batch
        process_events_batch.delay()
        process_events_batch.delay()

        self.assertEqual(
            ProcessedEventLog.objects.filter(event=event).count(),
            1
        )

    def test_recovery_moves_stuck_processing_to_queued(self):
        self.client.post(
            self.url,
            self._valid_payload(),
            format="json",
            HTTP_X_API_KEY="test-api-key",
        )

        event = Event.objects.get()
        state = event.processing_state

        state.status = StatusEnum.PROCESSING
        state.locked_at = timezone.now() - timedelta(minutes=10)
        state.save()

        recover_stuck_processing()

        state.refresh_from_db()
        self.assertEqual(state.status, StatusEnum.QUEUED)
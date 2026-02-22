from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone

from apps.accounts.models import User, APIKey
from apps.events.models import Event, ProcessingState, StatusEnum


class EventIngestTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass",
            role="admin"
        )

        self.api_key = APIKey.objects.create(
            user=self.user,
            key="test-api-key"
        )

        self.url = reverse("event-ingest")

    def test_event_ingest_creates_processing_state(self):
        payload = {
            "source": "payment-api",
            "event_type": "payment.success",
            "timestamp": timezone.now().isoformat(),
            "payload": {
                "order_id": "12345",
                "amount": 150.0
            }
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_API_KEY="test-api-key"
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(ProcessingState.objects.count(), 1)

        state = ProcessingState.objects.first()

        # task runs immediately.
        self.assertEqual(state.status, StatusEnum.PROCESSED)
        self.assertIsNotNone(state.event)

    def test_event_ingest_creates_processing_state_without_permission(self):
        self.user.role = "producer"
        self.user.save()

        payload = {
            "source": "payment-api",
            "event_type": "payment.success",
            "timestamp": timezone.now().isoformat(),
            "payload": {
                "order_id": "12345",
                "amount": 150.0
            }
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_API_KEY="test-api-key"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
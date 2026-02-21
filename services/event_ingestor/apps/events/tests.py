from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.events.models import Event


class EventModelTest(TestCase):

    def test_event_creation(self):
        User = get_user_model()
        user = User.objects.create(username="test")

        event = Event.objects.create(
            user=user,
            source="test",
            event_type="test.event",
            timestamp="2026-01-01T00:00:00Z",
            payload={"a": 1}
        )

        self.assertIsNotNone(event.id)
        self.assertEqual(event.source, "test")
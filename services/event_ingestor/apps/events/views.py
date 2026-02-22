from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import StatusEnum, ProcessingState
from .serializers import EventIngestSerializer
from ..common.permissions import HasAPIPermission
from .tasks import process_events_batch
from django.conf import settings


def enqueue_event(event):
    state = ProcessingState.objects.get(event=event)
    state.status = StatusEnum.QUEUED
    state.save(update_fields=["status"])

    # Due to integration tests
    def dispatch():
        process_events_batch.delay()

    if getattr(settings, "RUN_TASKS_IMMEDIATELY", False):
        dispatch()
    else:
        transaction.on_commit(dispatch)


class EventIngestView(APIView):
    required_permission = "events.post.event_ingest"
    permission_classes = [HasAPIPermission]

    def post(self, request):
        serializer = EventIngestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        event = serializer.save()

        ProcessingState.objects.create(
            event=event,
            status=StatusEnum.ACCEPTED
        )

        enqueue_event(event=event)

        return Response(
            {
                "status": "accepted",
                "event_id": str(event.id),
            },
            status=status.HTTP_202_ACCEPTED,
        )

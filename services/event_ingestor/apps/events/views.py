from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from .serializers import EventIngestSerializer
from ..common.permissions import HasAPIPermission


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

        return Response(
            {
                "status": "accepted",
                "event_id": str(event.id),
            },
            status=status.HTTP_202_ACCEPTED,
        )

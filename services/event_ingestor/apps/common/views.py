from rest_framework.response import Response
from rest_framework.views import APIView
from apps.common.permissions import HasAPIPermission


class HealthzView(APIView):
    required_permission = "view.get.healthz"
    permission_classes = [HasAPIPermission]

    def get(self, request):
        return Response({"status": "ok"})

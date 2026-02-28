from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import APIKey


class APIKeyIntrospectView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        api_key = request.query_params.get("token")
        if not api_key:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            key_obj = APIKey.objects.select_related("user").get(key=api_key)
        except APIKey.DoesNotExist:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        return Response(
            {
                "user_id": str(key_obj.user_id),
                "role": key_obj.user.role,
            }
        )
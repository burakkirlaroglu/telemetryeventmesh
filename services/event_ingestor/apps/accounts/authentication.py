from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIKey, User


class APIKeyAuthentication(BaseAuthentication):
    keyword = "X-API-Key"

    def authenticate(self, request) -> tuple[User, None] | None:
        api_key = request.headers.get(self.keyword)
        if not api_key:
            return None

        try:
            key = APIKey.objects.select_related("user").get(
                key=api_key, is_active=True
            )
        except APIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key")

        if not key.user.is_active:
            raise AuthenticationFailed("User inactive")

        return key.user, None

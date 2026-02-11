from rest_framework.permissions import BasePermission


class HasAPIPermission(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        required = getattr(view, "required_permission", None)
        if not required:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        return user.has_api_permission(required)

# apps/accounts/urls_internal.py
from django.urls import path
from .views import APIKeyIntrospectView

urlpatterns = [
    path("auth/introspect/", APIKeyIntrospectView.as_view()),
]
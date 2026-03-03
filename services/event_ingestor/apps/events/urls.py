from django.urls import path
from .views import EventIngestView, ExtinctEventListView

urlpatterns = [
    path("events/", EventIngestView.as_view(), name="event-ingest"),
    path("events/extincts/", ExtinctEventListView.as_view(), name="event-extincts"),
]

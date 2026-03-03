from rest_framework import serializers
from .models import Event, ProcessingState


class EventIngestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["source", "event_type", "timestamp", "payload"]

    def validate_event_type(self, value):
        if "." not in value:
            raise serializers.ValidationError(
                "event_type must contain namespace like cpu.usage"
            )
        return value

    def create(self, validated_data):
        request = self.context["request"]

        return Event.objects.create(
            user=request.user,
            **validated_data,
        )


class ExtinctEventSerializer(serializers.ModelSerializer):
    event_id = serializers.UUIDField(source="event.id")

    class Meta:
        model = ProcessingState
        fields = [
            "event_id",
            "retry_count",
            "last_error",
            "updated_at",
        ]

from rest_framework import serializers
from .models import Event


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

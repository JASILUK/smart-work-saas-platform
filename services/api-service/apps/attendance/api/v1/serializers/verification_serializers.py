# apps/attendance/api/v1/serializers/verification_serializers.py

from rest_framework import serializers


class GPSVerifyRequestSerializer(serializers.Serializer):
    latitude = serializers.FloatField(required=True, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=True, min_value=-180, max_value=180)


class GPSVerifyResponseSerializer(serializers.Serializer):
    verified = serializers.BooleanField()
    token = serializers.CharField()
    location_name = serializers.CharField()
    distance_meters = serializers.FloatField()
    expires_in_seconds = serializers.IntegerField()


class FaceVerifyRequestSerializer(serializers.Serializer):
    image_base64 = serializers.CharField(required=False, allow_blank=True)
    face_embedding = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        allow_empty=True,
        help_text="Browser-extracted face embedding vector"
    )
    verification_method = serializers.ChoiceField(
        choices=["browser_embedding", "backend_ai"],
        default="browser_embedding"
    )
    
    def validate(self, data):
        if not data.get("image_base64") and not data.get("face_embedding"):
            raise serializers.ValidationError(
                "Either image_base64 or face_embedding must be provided."
            )
        return data


class FaceVerifyResponseSerializer(serializers.Serializer):
    verified = serializers.BooleanField()
    token = serializers.CharField()
    confidence = serializers.FloatField()
    expires_in_seconds = serializers.IntegerField()
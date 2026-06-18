from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.attendance_location import AttendanceLocation
from apps.attendance.validators.attendance_location_validator import AttendanceLocationValidator


class AttendanceLocationListSerializer(serializers.ModelSerializer):
    """ Read-only list serializer targeting fast grid tracking arrays generation workflows. """
    class Meta:
        model = AttendanceLocation
        fields = ["id", "name", "address", "latitude", "longitude", "radius_meters", "is_active"]
        read_only_fields = fields


class AttendanceLocationDetailSerializer(serializers.ModelSerializer):
    """ Comprehensive audit read serializer providing access metadata tracking timelines. """
    class Meta:
        model = AttendanceLocation
        fields = [
            "id", "name", "address", "latitude", "longitude", 
            "radius_meters", "is_active", "created_at", "updated_at"
        ]
        read_only_fields = fields


class AttendanceLocationCreateSerializer(serializers.ModelSerializer):
    """ Validates entry field metrics constraints before reaching service processors. """
    address = serializers.CharField(required=False, allow_blank=True, default="")
    radius_meters = serializers.IntegerField(required=False, default=150)

    class Meta:
        model = AttendanceLocation
        fields = ["name", "address", "latitude", "longitude", "radius_meters"]

    def validate_latitude(self, value):
        AttendanceLocationValidator.validate_latitude(value)
        return value

    def validate_longitude(self, value):
        AttendanceLocationValidator.validate_longitude(value)
        return value

    def validate_radius_meters(self, value):
        AttendanceLocationValidator.validate_radius(value)
        return value


class AttendanceLocationUpdateSerializer(serializers.ModelSerializer):
    """ Processes partial configurations synchronization schema modification patches. """
    name = serializers.CharField(required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    radius_meters = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = AttendanceLocation
        fields = ["name", "address", "latitude", "longitude", "radius_meters", "is_active"]

    def validate_latitude(self, value):
        AttendanceLocationValidator.validate_latitude(value)
        return value

    def validate_longitude(self, value):
        AttendanceLocationValidator.validate_longitude(value)
        return value

    def validate_radius_meters(self, value):
        AttendanceLocationValidator.validate_radius(value)
        return value
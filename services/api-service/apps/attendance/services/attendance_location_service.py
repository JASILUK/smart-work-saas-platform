from typing import Any, Dict, Optional
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_location import AttendanceLocation
from apps.attendance.validators.attendance_location_validator import AttendanceLocationValidator


class AttendanceLocationService:
    """
    Manages structural data mutations for GPS Geofence operational configurations.
    """

    @classmethod
    @transaction.atomic
    def create_location(cls, *, company: Company, actor: Optional[Membership], validated_data: Dict[str, Any]) -> AttendanceLocation:
        """
        Initializes an operational geofence location for the tenant scope.
        Validates coordinate bounds and confirms corporate GPS activation eligibility.
        """
        # Business Rule 1 validation execution
        AttendanceLocationValidator.validate_gps_enabled(company=company)

        # Coordinate structural ranges verification checks
        AttendanceLocationValidator.validate_latitude(validated_data["latitude"])
        AttendanceLocationValidator.validate_longitude(validated_data["longitude"])
        AttendanceLocationValidator.validate_radius(validated_data.get("radius_meters", 150))

        return AttendanceLocation.objects.create(
            company=company,
            created_by=actor,
            name=validated_data["name"],
            address=validated_data.get("address", ""),
            latitude=validated_data["latitude"],
            longitude=validated_data["longitude"],
            radius_meters=validated_data.get("radius_meters", 150),
            is_active=validated_data.get("is_active", True)
        )

    @classmethod
    @transaction.atomic
    def update_location(cls, *, location: AttendanceLocation, validated_data: Dict[str, Any]) -> AttendanceLocation:
        """
        Updates parameters of an existing geofence record.
        If enabling an inactive perimeter, verifies that GPS remains active globally for the tenant.
        """
        company = location.company

        # If transaction attempts status switch back to active, execute Business Rule 1 check
        if validated_data.get("is_active", location.is_active) and not location.is_active:
            AttendanceLocationValidator.validate_gps_enabled(company=company)

        if "latitude" in validated_data:
            AttendanceLocationValidator.validate_latitude(validated_data["latitude"])
            location.latitude = validated_data["latitude"]

        if "longitude" in validated_data:
            AttendanceLocationValidator.validate_longitude(validated_data["longitude"])
            location.longitude = validated_data["longitude"]

        if "radius_meters" in validated_data:
            AttendanceLocationValidator.validate_radius(validated_data["radius_meters"])
            location.radius_meters = validated_data["radius_meters"]

        if "name" in validated_data:
            location.name = validated_data["name"]

        if "address" in validated_data:
            location.address = validated_data["address"]

        if "is_active" in validated_data:
            location.is_active = validated_data["is_active"]

        location.save()
        return location

    @classmethod
    @transaction.atomic
    def deactivate_location(cls, *, location: AttendanceLocation) -> AttendanceLocation:
        """ Softly deactivates a perimeter point to preserve historic lookup contexts. """
        if location.is_active:
            location.is_active = False
            location.save(update_fields=["is_active", "updated_at"])
        return location

    @classmethod
    @transaction.atomic
    def activate_location(cls, *, location: AttendanceLocation) -> AttendanceLocation:
        """ Activates a soft-deactivated perimeter if company global rules allow. """
        if not location.is_active:
            AttendanceLocationValidator.validate_gps_enabled(company=location.company)
            location.is_active = True
            location.save(update_fields=["is_active", "updated_at"])
        return location
from django.db import models

class HRReviewStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Review"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_REVIEW = "IN_REVIEW", "In Review"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"
    ESCALATED = "ESCALATED", "Escalated"

class HRReviewPriority(models.TextChoices):
    CRITICAL = "CRITICAL", "Critical Priority"
    HIGH = "HIGH", "High Priority"
    MEDIUM = "MEDIUM", "Medium Priority"
    LOW = "LOW", "Low Priority"

class HRAnomalyType(models.TextChoices):
    MISSING_CHECKOUT = "MISSING_CHECKOUT", "Missing Shift Checkout"
    AUTO_CLOSED = "AUTO_CLOSED", "Machine Automated Closure"
    LATE_ARRIVAL = "LATE_ARRIVAL", "Extreme Late Arrival"
    GEOLOCATION_VIOLATION = "GPS_VIOLATION", "GPS Outside Geofence"
    REVIEW_REQUIRED = "NEEDS_REVIEW", "Forced Administrative Review"
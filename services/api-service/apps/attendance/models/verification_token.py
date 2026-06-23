# apps/attendance/models/verification_token.py

import uuid
from django.db import models
from django.utils import timezone


class VerificationToken(models.Model):
    """
    One-time secure verification tokens for attendance method validation.
    Prevents frontend spoofing by making verification server-authoritative.
    """
    
    TOKEN_TYPE_CHOICES = [
        ("FACE", "Face Verification"),
        ("GPS", "GPS Verification"),
        ("QR", "QR Code Verification"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPE_CHOICES)
    
    company = models.ForeignKey(
        "companies.Company", 
        on_delete=models.CASCADE,
        related_name="verification_tokens"
    )
    membership = models.ForeignKey(
        "companies.Membership", 
        on_delete=models.CASCADE,
        related_name="verification_tokens"
    )
    
    face_enrollment = models.ForeignKey(
        "attendance.FaceEnrollment", 
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        related_name="verification_tokens"
    )
    location = models.ForeignKey(
        "attendance.AttendanceLocation", 
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        related_name="verification_tokens"
    )
    
    verification_payload = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = "attendance_verification_tokens"
        indexes = [
            models.Index(fields=["company", "membership", "token_type", "is_used"]),
            models.Index(fields=["expires_at"]),
        ]
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired
    
    def mark_used(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])
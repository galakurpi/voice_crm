from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Use Django's built-in User model (which has email and password)
# We'll extend it with a custom model if needed, but Django's User is secure by default
# Passwords are automatically hashed using PBKDF2

class SecurityLog(models.Model):
    """Audit log for security events like login attempts, failed authentications, etc."""
    event_type = models.CharField(max_length=50)  # e.g., 'login_success', 'login_failed', 'logout', 'register'
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)  # Additional context
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['event_type']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.user or 'Anonymous'} - {self.timestamp}"

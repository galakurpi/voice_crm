from django.contrib import admin
from .models import SecurityLog

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    """Admin interface for security audit logs."""
    list_display = ('event_type', 'user', 'ip_address', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('event_type', 'user__email', 'user__username', 'ip_address')
    readonly_fields = ('event_type', 'user', 'ip_address', 'user_agent', 'details', 'timestamp')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        # Prevent manual creation of security logs
        return False

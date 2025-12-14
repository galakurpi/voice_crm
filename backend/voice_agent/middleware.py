import time
from django.http import JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware to prevent brute force attacks.
    Limits login attempts per IP address.
    """
    def process_request(self, request):
        # Only apply rate limiting to login endpoint
        if request.path == '/auth/login' and request.method == 'POST':
            ip_address = self.get_client_ip(request)
            cache_key = f'login_attempts_{ip_address}'
            
            # Get current attempt count
            attempts = cache.get(cache_key, 0)
            
            # Limit: 5 attempts per 15 minutes
            if attempts >= 5:
                return JsonResponse({
                    'error': 'Too many login attempts. Please try again in 15 minutes.'
                }, status=429)
            
            # Increment attempts counter (expires in 15 minutes)
            cache.set(cache_key, attempts + 1, 900)  # 900 seconds = 15 minutes
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

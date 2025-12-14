import json
import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import SecurityLog

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_security_event(event_type, request, user=None, details=None):
    """Log security events for audit trail."""
    try:
        SecurityLog.objects.create(
            event_type=event_type,
            user=user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details=details or {}
        )
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")

# Note: CSRF exemption is needed for API endpoints that don't use CSRF tokens
# In production, consider using CSRF tokens or API keys instead
@csrf_exempt
@require_http_methods(["POST"])
def register_view(request):
    """Register a new user with email and password."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        username = data.get('username', email.split('@')[0])  # Use email prefix as username
        
        # Validation
        if not email or '@' not in email:
            log_security_event('register_failed', request, details={'reason': 'invalid_email'})
            return JsonResponse({'error': 'Valid email is required'}, status=400)
        
        if not password or len(password) < 8:
            log_security_event('register_failed', request, details={'reason': 'weak_password'})
            return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            log_security_event('register_failed', request, details={'reason': 'email_exists'})
            return JsonResponse({'error': 'Email already registered'}, status=400)
        
        if User.objects.filter(username=username).exists():
            # If username exists, append number
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
        
        # Create user - Django automatically hashes the password securely
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password  # Django hashes this automatically using PBKDF2
        )
        
        log_security_event('register_success', request, user=user)
        logger.info(f"User registered: {email}")
        
        return JsonResponse({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        log_security_event('register_error', request, details={'error': str(e)})
        return JsonResponse({'error': 'Registration failed'}, status=500)

# Note: CSRF exemption is needed for API endpoints that don't use CSRF tokens
# In production, consider using CSRF tokens or API keys instead
@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """Authenticate user and create session."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            log_security_event('login_failed', request, details={'reason': 'missing_credentials'})
            return JsonResponse({'error': 'Email and password required'}, status=400)
        
        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            log_security_event('login_failed', request, details={'reason': 'user_not_found', 'email': email})
            return JsonResponse({'error': 'Invalid email or password'}, status=401)
        
        # Authenticate - Django checks password hash automatically
        user = authenticate(request, username=user.username, password=password)
        
        if user is not None:
            # Login successful - Django creates secure session
            login(request, user)
            log_security_event('login_success', request, user=user)
            logger.info(f"User logged in: {email}")
            
            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            })
        else:
            log_security_event('login_failed', request, user=user, details={'reason': 'invalid_password'})
            return JsonResponse({'error': 'Invalid email or password'}, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        log_security_event('login_error', request, details={'error': str(e)})
        return JsonResponse({'error': 'Login failed'}, status=500)

@require_http_methods(["POST"])
def logout_view(request):
    """Logout user and destroy session."""
    if request.user.is_authenticated:
        user = request.user
        logout(request)
        log_security_event('logout', request, user=user)
        logger.info(f"User logged out: {user.email}")
        return JsonResponse({'success': True, 'message': 'Logged out successfully'})
    else:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

@require_http_methods(["GET"])
def check_auth_view(request):
    """Check if user is authenticated."""
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email
            }
        })
    else:
        return JsonResponse({'authenticated': False})

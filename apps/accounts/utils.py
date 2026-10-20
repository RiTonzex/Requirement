import time
from django.core.cache import cache
from django.conf import settings
from core.views import get_client_ip


def get_login_rate_limit_keys(request, username):
    ip = get_client_ip(request) or '127.0.0.1'
    clean_user = str(username or '').strip().lower()
    key_attempts = f"login_attempts_{ip}_{clean_user}"
    key_lockout_time = f"login_lockout_{ip}_{clean_user}"
    return key_attempts, key_lockout_time


def check_login_rate_limit(request, username):
    """
    Check if the user/IP is currently locked out from logging in.
    Returns (is_locked, remaining_seconds, current_attempts)
    """
    key_attempts, key_lockout_time = get_login_rate_limit_keys(request, username)
    
    lockout_until = cache.get(key_lockout_time)
    if lockout_until:
        now = time.time()
        if now < lockout_until:
            remaining = int(lockout_until - now)
            return True, remaining, settings.LOGIN_RATE_LIMIT_ATTEMPTS
        else:
            # Lockout expired
            cache.delete(key_lockout_time)
            cache.delete(key_attempts)

    attempts = cache.get(key_attempts, 0)
    return False, 0, attempts


def record_failed_login(request, username):
    """
    Record a failed login attempt. If limit exceeded, lock out for configured duration.
    Returns (is_locked_now, remaining_seconds, new_attempts)
    """
    key_attempts, key_lockout_time = get_login_rate_limit_keys(request, username)
    limit = getattr(settings, 'LOGIN_RATE_LIMIT_ATTEMPTS', 5)
    lockout_duration = getattr(settings, 'LOGIN_RATE_LIMIT_LOCKOUT_SECONDS', 300)

    attempts = cache.get(key_attempts, 0) + 1
    cache.set(key_attempts, attempts, timeout=lockout_duration)

    if attempts >= limit:
        lockout_until = time.time() + lockout_duration
        cache.set(key_lockout_time, lockout_until, timeout=lockout_duration)
        return True, lockout_duration, attempts

    return False, 0, attempts


def reset_failed_login(request, username):
    """
    Reset failed login attempts upon successful login.
    """
    key_attempts, key_lockout_time = get_login_rate_limit_keys(request, username)
    cache.delete(key_attempts)
    cache.delete(key_lockout_time)

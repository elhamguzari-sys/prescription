# prescript/middleware.py

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404


# ═══════════════════════════════════════════════════════════════════
# 🔒 Login Required Middleware
#
# Blocks EVERYTHING except:
#   • The login page
#   • The logout page (POST)
#   • Django admin login
#   • Static and media files (in DEBUG)
#   • URLs explicitly whitelisted below
# ═══════════════════════════════════════════════════════════════════

class LoginRequiredMiddleware:
    """
    Redirects anonymous users to the login page for any view
    that is not explicitly whitelisted.
    """

    # URL names that do NOT require login
    WHITELISTED_URL_NAMES = {
        'login',
        'logout',
        # Django admin URLs (login needs to be reachable)
        'admin:login',
        'admin:logout',
    }

    # URL prefixes that do NOT require login
    WHITELISTED_PREFIXES = (
        '/static/',
        '/media/',
        '/admin/login/',
        '/admin/logout/',
        '/login/',
        '/logout/',
        '/favicon.ico',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── Skip auth check for already-authenticated users ──
        if request.user.is_authenticated:
            return self.get_response(request)

        # ── Skip whitelisted prefixes ──
        path = request.path_info
        for prefix in self.WHITELISTED_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        # ── Try to match the URL name ──
        try:
            match = resolve(path)
            url_name = match.view_name

            if url_name in self.WHITELISTED_URL_NAMES:
                return self.get_response(request)

            # Also allow admin URL names (admin:*) unless it's the login
            if url_name and url_name.startswith('admin:'):
                return self.get_response(request)

        except Resolver404:
            # Path doesn't match any URL — let Django handle 404
            pass

        # ── Otherwise: redirect to login ──
        login_url = reverse('login')
        return redirect(f'{login_url}?next={path}')


# ═══════════════════════════════════════════════════════════════════
# 🔄 Force Logout Middleware (optional)
#
# If you want the login to expire after N minutes of inactivity,
# you can add this. Otherwise, skip it.
# ═══════════════════════════════════════════════════════════════════
#
# class AutoLogoutMiddleware:
#     ...
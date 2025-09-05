from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import login, get_user_model
from django.contrib.auth.models import AnonymousUser
from core.auth.supabase_auth import SupabaseAuthentication
from datetime import datetime, timezone


class SupabaseCookieAuthMiddleware(MiddlewareMixin):
    """Authenticate non-API requests using a Supabase JWT stored in a cookie.

    If no Authorization header is present and user is anonymous, read 'sb-access-token' or 'sb:token'
    cookie, validate it, and log the user in for Django template views.
    """

    def process_request(self, request):
        if getattr(request, 'user', None) and not isinstance(request.user, AnonymousUser) and request.user.is_authenticated:
            return

        token = request.COOKIES.get('sb-access-token') or request.COOKIES.get('sb:token')
        if not token:
            return
        # Ensure DRF sees the token for API calls
        request.META['HTTP_AUTHORIZATION'] = request.META.get('HTTP_AUTHORIZATION') or f'Bearer {token}'
        try:
            payload = SupabaseAuthentication.decode_token(token)
            email = payload.get('email') or payload.get('user_metadata', {}).get('email')
            if not email:
                return
            User = get_user_model()
            user, _ = User.objects.get_or_create(email=email, defaults={'username': email.split('@')[0]})
            # Log user into Django session for template views
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            # Optionally set session expiry to token exp
            exp = payload.get('exp')
            if exp:
                # exp is seconds since epoch
                now = datetime.now(timezone.utc).timestamp()
                seconds = max(60, int(exp - now))
                request.session.set_expiry(seconds)
        except Exception:
            # Silently ignore invalid cookies
            return


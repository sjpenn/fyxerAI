import time
import json
import requests
from typing import Optional, Tuple
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
import jwt


_JWKS_CACHE = {
    'keys': None,
    'fetched_at': 0,
    'ttl': 3600,  # 1 hour
}


def _get_jwks() -> dict:
    now = time.time()
    if _JWKS_CACHE['keys'] and (now - _JWKS_CACHE['fetched_at'] < _JWKS_CACHE['ttl']):
        return _JWKS_CACHE['keys']
    jwks_url = getattr(settings, 'SUPABASE_JWKS_URL', None) or (
        f"{getattr(settings, 'SUPABASE_URL', '').rstrip('/')}/auth/v1/keys"
    )
    if not jwks_url:
        raise exceptions.AuthenticationFailed('Supabase JWKS URL not configured')
    resp = requests.get(jwks_url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    _JWKS_CACHE['keys'] = data
    _JWKS_CACHE['fetched_at'] = now
    return data


def _get_public_key(token_headers: dict) -> Optional[str]:
    kid = token_headers.get('kid')
    jwks = _get_jwks()
    for key in jwks.get('keys', []):
        if key.get('kid') == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    return None


class SupabaseAuthentication(BaseAuthentication):
    """Authenticate DRF requests using Supabase JWT (GoTrue).

    Expects Authorization: Bearer <JWT> header. On success, ties/creates a Django user by email.
    """

    @staticmethod
    def decode_token(token: str) -> dict:
        unverified_headers = jwt.get_unverified_header(token)
        public_key = _get_public_key(unverified_headers)
        if not public_key:
            raise exceptions.AuthenticationFailed('Invalid token: unknown key id')
        audience = getattr(settings, 'SUPABASE_JWT_AUD', None) or 'authenticated'
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=audience,
            options={'verify_exp': True}
        )
        return payload

    def authenticate(self, request) -> Optional[Tuple[object, None]]:
        auth = request.headers.get('Authorization') or ''
        if not auth.startswith('Bearer '):
            return None
        token = auth.split(' ', 1)[1].strip()
        if not token:
            return None

        try:
            payload = self.decode_token(token)

            email = payload.get('email') or payload.get('user_metadata', {}).get('email')
            sub = payload.get('sub')
            if not email:
                raise exceptions.AuthenticationFailed('Token missing email claim')

            User = get_user_model()
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                }
            )
            # Optionally store supabase user id
            if not user.first_name and payload.get('user_metadata', {}).get('full_name'):
                user.first_name = payload['user_metadata']['full_name']
                user.save(update_fields=['first_name'])

            return (user, None)
        except requests.RequestException as e:
            raise exceptions.AuthenticationFailed(f'JWKS fetch failed: {e}')
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {e}')

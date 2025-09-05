from django.core.management.base import BaseCommand
from django.conf import settings
import requests


class Command(BaseCommand):
    help = 'Validate Supabase configuration and JWKS accessibility.'

    def handle(self, *args, **opts):
        url = getattr(settings, 'SUPABASE_URL', '')
        jwks = getattr(settings, 'SUPABASE_JWKS_URL', '') or (url.rstrip('/') + '/auth/v1/keys' if url else '')
        self.stdout.write(f'SUPABASE_URL: {url}')
        self.stdout.write(f'JWKS URL: {jwks}')
        if not jwks:
            self.stderr.write(self.style.ERROR('JWKS URL not configured'))
            return
        try:
            resp = requests.get(jwks, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            keys = data.get('keys', [])
            self.stdout.write(self.style.SUCCESS(f'JWKS fetch OK, keys: {len(keys)}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'JWKS fetch failed: {e}'))


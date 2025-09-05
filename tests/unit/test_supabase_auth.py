import types
import pytest
from django.test import RequestFactory
from core.auth.supabase_auth import SupabaseAuthentication


@pytest.mark.django_db
def test_supabase_auth_creates_user(monkeypatch):
    # Stub JWKS and jwt.decode to avoid real network/crypto
    monkeypatch.setattr('core.auth.supabase_auth._get_jwks', lambda: {'keys': [{'kid': 'abc'}]})

    class DummyRSA:
        pass

    monkeypatch.setattr('core.auth.supabase_auth.jwt.algorithms.RSAAlgorithm.from_jwk', lambda s: DummyRSA())

    claims = {
        'email': 'authuser@example.com',
        'aud': 'authenticated',
        'sub': '123',
    }
    monkeypatch.setattr('core.auth.supabase_auth.jwt.get_unverified_header', lambda t: {'kid': 'abc'})
    monkeypatch.setattr('core.auth.supabase_auth.jwt.decode', lambda t, k, algorithms, audience, options: claims)

    rf = RequestFactory()
    req = rf.get('/api/health/', HTTP_AUTHORIZATION='Bearer fake.jwt.token')
    user_auth = SupabaseAuthentication()
    user, _ = user_auth.authenticate(req)
    assert user.email == 'authuser@example.com'

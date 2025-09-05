#!/usr/bin/env python3
"""
Test script to verify Gmail OAuth fix
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fyxerai_assistant.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model

def test_oauth_fix():
    print("🔧 Testing Gmail OAuth Flow Fix...")
    
    # Check that OAUTHLIB_INSECURE_TRANSPORT is set
    insecure_transport = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT')
    print(f"✅ OAUTHLIB_INSECURE_TRANSPORT: {insecure_transport}")
    
    if insecure_transport != '1':
        print("❌ OAUTHLIB_INSECURE_TRANSPORT is not set to '1'")
        return False
    
    print(f"✅ DEBUG mode: {settings.DEBUG}")
    print(f"✅ Google Client ID configured: {bool(getattr(settings, 'GOOGLE_CLIENT_ID', None))}")
    print(f"✅ Google Client Secret configured: {bool(getattr(settings, 'GOOGLE_CLIENT_SECRET', None))}")
    
    # Check user exists
    User = get_user_model()
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ Admin user exists: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ Admin user not found")
        return False
    
    return True

if __name__ == '__main__':
    print("🧪 OAuth Fix Test Suite\n")
    
    success = test_oauth_fix()
    
    if success:
        print("\n✅ OAuth fix configuration looks correct!")
        print("📝 The HTTPS requirement error should be resolved.")
        print("🎯 Try the OAuth flow manually at: http://localhost:8000/auth/gmail/login/")
    else:
        print("\n❌ OAuth fix configuration has issues.")
    
    sys.exit(0 if success else 1)
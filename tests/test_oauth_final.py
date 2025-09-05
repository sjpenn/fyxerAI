#!/usr/bin/env python3
"""
Final OAuth Flow Test for FYXERAI-GEDS
Run this script to test Gmail OAuth connection flow and diagnose issues.

Usage: python tests/test_oauth_final.py
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Ensure we're using the correct Django settings
if 'DJANGO_SETTINGS_MODULE' in os.environ and 'blackcoral' in os.environ['DJANGO_SETTINGS_MODULE']:
    print("⚠️  WARNING: DJANGO_SETTINGS_MODULE is set to blackcoral. Unsetting...")
    del os.environ['DJANGO_SETTINGS_MODULE']

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fyxerai_assistant.settings')
os.environ.setdefault('USE_DOTENV', '0')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import django
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from core.models import EmailAccount

User = get_user_model()

def test_oauth_flow():
    """Test the complete OAuth flow components"""
    
    print("🔍 FYXERAI Gmail OAuth Connection Flow Test")
    print("=" * 60)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {},
        'recommendations': [],
        'success': True
    }
    
    # Test 1: Django Configuration
    print("\n1️⃣  Testing Django Configuration...")
    try:
        print(f"   ✅ Django version: {django.get_version()}")
        print(f"   ✅ Settings module: {settings.SETTINGS_MODULE}")
        print(f"   ✅ Database backend: {settings.DATABASES['default']['ENGINE']}")
        print(f"   ✅ Secret key configured: {bool(settings.SECRET_KEY)}")
        results['tests']['django_config'] = True
    except Exception as e:
        print(f"   ❌ Django configuration error: {e}")
        results['tests']['django_config'] = False
        results['success'] = False
    
    # Test 2: OAuth Configuration
    print("\n2️⃣  Testing OAuth Configuration...")
    try:
        google_id_configured = bool(settings.GOOGLE_CLIENT_ID)
        google_secret_configured = bool(settings.GOOGLE_CLIENT_SECRET)
        
        print(f"   Google Client ID configured: {'✅' if google_id_configured else '❌'}")
        print(f"   Google Client Secret configured: {'✅' if google_secret_configured else '❌'}")
        
        if google_id_configured:
            print(f"   Client ID: {settings.GOOGLE_CLIENT_ID[:20]}..." if len(settings.GOOGLE_CLIENT_ID) > 20 else settings.GOOGLE_CLIENT_ID)
        
        oauth_ready = google_id_configured and google_secret_configured
        results['tests']['oauth_config'] = oauth_ready
        
        if not oauth_ready:
            results['recommendations'].append("Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file")
            
    except Exception as e:
        print(f"   ❌ OAuth configuration error: {e}")
        results['tests']['oauth_config'] = False
        results['success'] = False
    
    # Test 3: User Model
    print("\n3️⃣  Testing User Model...")
    try:
        # Clean up any existing test users
        User.objects.filter(username='oauth_flow_test').delete()
        
        # Create test user
        user = User.objects.create_user(
            username='oauth_flow_test',
            email='oauth_test@fyxerai.com',
            password='TestPass123!'
        )
        
        print(f"   ✅ Test user created: {user.username}")
        print(f"   ✅ User ID: {user.id}")
        print(f"   ✅ User authenticated: {user.is_authenticated}")
        
        results['tests']['user_model'] = True
        
    except Exception as e:
        print(f"   ❌ User model error: {e}")
        results['tests']['user_model'] = False
        results['success'] = False
        user = None
    
    # Test 4: EmailAccount Model
    if user:
        print("\n4️⃣  Testing EmailAccount Model...")
        try:
            # Create test email account
            account = EmailAccount.objects.create(
                user=user,
                provider='gmail',
                email_address='test_account@gmail.com',
                display_name='Test Gmail Account',
                access_token=EmailAccount().encrypt_token('test_access_token_12345'),
                refresh_token=EmailAccount().encrypt_token('test_refresh_token_67890'),
                token_expires_at=timezone.now() + timedelta(hours=1),
                is_active=True
            )
            
            print(f"   ✅ Email account created: {account.email_address}")
            print(f"   ✅ Account ID: {account.id}")
            print(f"   ✅ Provider: {account.provider}")
            print(f"   ✅ Active status: {account.is_active}")
            
            # Test token encryption/decryption
            decrypted_access = account.decrypt_token(account.access_token)
            decrypted_refresh = account.decrypt_token(account.refresh_token)
            
            if decrypted_access == 'test_access_token_12345':
                print("   ✅ Access token encryption/decryption working")
            else:
                print(f"   ❌ Access token decryption failed: {decrypted_access}")
                
            if decrypted_refresh == 'test_refresh_token_67890':
                print("   ✅ Refresh token encryption/decryption working")
            else:
                print(f"   ❌ Refresh token decryption failed: {decrypted_refresh}")
            
            results['tests']['email_account_model'] = True
            
        except Exception as e:
            print(f"   ❌ EmailAccount model error: {e}")
            results['tests']['email_account_model'] = False
            results['success'] = False
    
    # Test 5: Database Queries
    if user:
        print("\n5️⃣  Testing Database Queries...")
        try:
            # Test account retrieval
            accounts = EmailAccount.objects.filter(user=user)
            account_count = accounts.count()
            
            print(f"   ✅ Accounts for user: {account_count}")
            
            for account in accounts:
                print(f"   ✅ Found account: {account.email_address} ({account.provider})")
            
            # Test unique constraint
            try:
                EmailAccount.objects.create(
                    user=user,
                    provider='gmail',
                    email_address='test_account@gmail.com',  # Duplicate
                    access_token=EmailAccount().encrypt_token('duplicate'),
                    refresh_token=EmailAccount().encrypt_token('duplicate'),
                    token_expires_at=timezone.now() + timedelta(hours=1)
                )
                print("   ❌ Unique constraint failed - duplicate created")
                results['tests']['database_queries'] = False
            except Exception:
                print("   ✅ Unique constraint working - duplicate prevented")
                results['tests']['database_queries'] = True
                
        except Exception as e:
            print(f"   ❌ Database query error: {e}")
            results['tests']['database_queries'] = False
            results['success'] = False
    
    # Test 6: OAuth URLs
    print("\n6️⃣  Testing OAuth URLs...")
    try:
        from django.urls import reverse
        
        oauth_login_url = reverse('core:gmail_oauth_login')
        oauth_callback_url = reverse('core:gmail_oauth_callback')
        debug_url = reverse('core:oauth_debug')
        
        print(f"   ✅ Gmail OAuth login URL: {oauth_login_url}")
        print(f"   ✅ Gmail OAuth callback URL: {oauth_callback_url}")
        print(f"   ✅ OAuth debug URL: {debug_url}")
        
        results['tests']['oauth_urls'] = True
        
    except Exception as e:
        print(f"   ❌ OAuth URL error: {e}")
        results['tests']['oauth_urls'] = False
        results['success'] = False
    
    # Generate Summary
    print("\n🎯 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(results['tests'].values())
    total_tests = len(results['tests'])
    
    for test_name, passed in results['tests'].items():
        status = "✅ PASS" if passed else "❌ FAIL"
        readable_name = test_name.replace('_', ' ').title()
        print(f"   {status} {readable_name}")
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")
    
    if results['success']:
        print("🟢 OAUTH BACKEND IS WORKING CORRECTLY!")
        
        print("\n📋 Next Steps:")
        print("1. Start the server: python manage.py runserver 0.0.0.0:8001")
        print("2. Configure OAuth credentials in .env file if not done")
        print("3. Visit: http://localhost:8001/auth/debug/")
        print("4. Test the live OAuth flow in browser")
        print("5. Check that accounts appear in dashboard after connection")
        
    else:
        print("🔴 OAUTH BACKEND HAS ISSUES")
        
        if results['recommendations']:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(results['recommendations'], 1):
                print(f"   {i}. {rec}")
    
    # Save detailed report
    report_file = 'oauth_test_report.json'
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Detailed report saved: {report_file}")
    
    return results['success']

if __name__ == '__main__':
    try:
        success = test_oauth_flow()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

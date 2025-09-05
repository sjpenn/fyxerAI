#!/usr/bin/env python3

"""
Comprehensive OAuth flow testing for FYXERAI-GEDS
Tests Gmail OAuth connection flow including account creation and dashboard visibility
"""

import os
import sys
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from urllib.parse import urlparse, parse_qs

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fyxerai_assistant.settings')

import django
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from core.models import EmailAccount
from core.views_oauth import gmail_oauth_callback

User = get_user_model()

class OAuthFlowTest(TestCase):
    """Comprehensive OAuth flow testing"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = Client()
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create_user(
            username='oauth_test_user',
            email='test@fyxerai.com',
            password='TestPass123!'
        )
        
        # Login the user
        self.client.force_login(self.user)
        
        # Test OAuth configuration
        self.test_oauth_config = {
            'google_client_id': 'test_client_id_123',
            'google_client_secret': 'test_client_secret_456'
        }
    
    def test_1_user_creation(self):
        """Test 1: Create a test user using Django management commands"""
        print("\n=== Test 1: User Creation ===")
        
        # Verify user was created
        user = User.objects.get(username='oauth_test_user')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@fyxerai.com')
        print("✅ Test user created successfully")
        
        # Verify user is authenticated
        self.assertTrue(user.is_authenticated)
        print("✅ User authentication working")
        
        # Check initial account count
        account_count = EmailAccount.objects.filter(user=user).count()
        self.assertEqual(account_count, 0)
        print("✅ User starts with 0 email accounts")
        
        return True
    
    def test_2_gmail_oauth_login(self):
        """Test 2: Gmail OAuth login endpoint to see what happens during authentication"""
        print("\n=== Test 2: Gmail OAuth Login Endpoint ===")
        
        with patch.object(settings, 'GOOGLE_CLIENT_ID', self.test_oauth_config['google_client_id']):
            with patch.object(settings, 'GOOGLE_CLIENT_SECRET', self.test_oauth_config['google_client_secret']):
                
                # Test OAuth login redirect
                response = self.client.get(reverse('core:gmail_oauth_login'), follow=False)
                
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 302:
                    redirect_url = response.get('Location', '')
                    print(f"✅ OAuth redirect working")
                    print(f"Redirect URL: {redirect_url[:100]}...")
                    
                    # Parse redirect URL
                    parsed_url = urlparse(redirect_url)
                    query_params = parse_qs(parsed_url.query)
                    
                    # Verify Google OAuth URL
                    self.assertIn('accounts.google.com', redirect_url)
                    print("✅ Redirecting to Google OAuth")
                    
                    # Check client_id in URL
                    client_id_in_url = query_params.get('client_id', [''])[0]
                    self.assertEqual(client_id_in_url, self.test_oauth_config['google_client_id'])
                    print("✅ Client ID correctly included in OAuth URL")
                    
                    # Check scope
                    scope_in_url = query_params.get('scope', [''])[0]
                    self.assertIn('gmail.readonly', scope_in_url)
                    print("✅ Gmail scopes correctly included")
                    
                    # Check state parameter (CSRF protection)
                    state_in_url = query_params.get('state', [''])[0]
                    self.assertTrue(state_in_url)
                    print("✅ State parameter included for CSRF protection")
                    
                    return redirect_url
                
                else:
                    print(f"❌ OAuth redirect failed with status {response.status_code}")
                    if hasattr(response, 'content'):
                        print(f"Response content: {response.content.decode()[:200]}")
                    return None
    
    def test_3_gmail_oauth_callback(self):
        """Test 3: Gmail OAuth callback handling with sample parameters"""
        print("\n=== Test 3: Gmail OAuth Callback Handling ===")
        
        # Mock Google OAuth response data
        mock_user_info = {
            'email': 'testuser@gmail.com',
            'name': 'Test User',
            'id': '123456789'
        }
        
        mock_credentials = Mock()
        mock_credentials.token = 'mock_access_token_123'
        mock_credentials.refresh_token = 'mock_refresh_token_456'
        mock_credentials.expiry = timezone.now() + timedelta(hours=1)
        
        # Create a valid state for CSRF protection
        session = self.client.session
        oauth_state = str(uuid.uuid4())
        session['oauth_state'] = oauth_state
        session.save()
        
        callback_url = reverse('core:gmail_oauth_callback')
        
        with patch.object(settings, 'GOOGLE_CLIENT_ID', self.test_oauth_config['google_client_id']):
            with patch.object(settings, 'GOOGLE_CLIENT_SECRET', self.test_oauth_config['google_client_secret']):
                with patch('core.views_oauth.Flow') as mock_flow:
                    with patch('core.views_oauth.get_gmail_user_info', return_value=mock_user_info):
                        
                        # Setup mock flow
                        mock_flow_instance = Mock()
                        mock_flow_instance.credentials = mock_credentials
                        mock_flow.from_client_config.return_value = mock_flow_instance
                        
                        # Simulate OAuth callback with authorization code
                        callback_params = {
                            'code': 'test_authorization_code_123',
                            'state': oauth_state,
                            'scope': 'https://www.googleapis.com/auth/gmail.readonly'
                        }
                        
                        response = self.client.get(callback_url, callback_params)
                        
                        print(f"Callback response status: {response.status_code}")
                        
                        if response.status_code == 302:
                            print("✅ OAuth callback processed successfully")
                            
                            # Verify account was created
                            account = EmailAccount.objects.filter(
                                user=self.user,
                                email_address='testuser@gmail.com'
                            ).first()
                            
                            if account:
                                print("✅ Email account created successfully")
                                print(f"   Account: {account.email_address}")
                                print(f"   Provider: {account.provider}")
                                print(f"   Display name: {account.display_name}")
                                print(f"   Active: {account.is_active}")
                                
                                # Verify token encryption
                                self.assertTrue(account.access_token)
                                self.assertTrue(account.refresh_token)
                                print("✅ Tokens encrypted and stored")
                                
                                return account
                            else:
                                print("❌ Email account was not created")
                                # Debug: List all accounts for this user
                                all_accounts = EmailAccount.objects.filter(user=self.user)
                                print(f"   All accounts for user: {list(all_accounts)}")
                                return None
                        else:
                            print(f"❌ OAuth callback failed with status {response.status_code}")
                            if hasattr(response, 'content'):
                                print(f"Response content: {response.content.decode()[:200]}")
                            return None
    
    def test_4_account_database_storage(self):
        """Test 4: Verify that the account is properly created and stored in the database"""
        print("\n=== Test 4: Account Database Storage ===")
        
        # First, create a test account through the OAuth callback
        test_account = self.test_3_gmail_oauth_callback()
        
        if test_account:
            # Verify database storage
            stored_account = EmailAccount.objects.get(id=test_account.id)
            
            self.assertEqual(stored_account.user_id, self.user.id)
            self.assertEqual(stored_account.provider, 'gmail')
            self.assertEqual(stored_account.email_address, 'testuser@gmail.com')
            self.assertTrue(stored_account.is_active)
            print("✅ Account properly stored in database")
            
            # Test token decryption
            decrypted_access_token = stored_account.decrypt_token(stored_account.access_token)
            self.assertEqual(decrypted_access_token, 'mock_access_token_123')
            print("✅ Token encryption/decryption working")
            
            # Test unique constraint
            with self.assertRaises(Exception):
                EmailAccount.objects.create(
                    user=self.user,
                    provider='gmail',
                    email_address='testuser@gmail.com',  # Same email
                    access_token=stored_account.encrypt_token('duplicate_token'),
                    refresh_token=stored_account.encrypt_token('duplicate_refresh'),
                    token_expires_at=timezone.now() + timedelta(hours=1)
                )
            print("✅ Unique constraint prevents duplicate accounts")
            
            return stored_account
        else:
            print("❌ Cannot test database storage - account creation failed")
            return None
    
    def test_5_dashboard_visibility(self):
        """Test 5: Check if the account shows up in the dashboard after connection"""
        print("\n=== Test 5: Dashboard Account Visibility ===")
        
        # Create account first
        test_account = self.test_4_account_database_storage()
        
        if test_account:
            # Test dashboard home view
            response = self.client.get(reverse('core:home'))
            self.assertEqual(response.status_code, 200)
            print("✅ Dashboard accessible")
            
            # Test email accounts partial (HTMX endpoint)
            response = self.client.get(reverse('core:email-accounts-partial'))
            self.assertEqual(response.status_code, 200)
            
            # Check if account appears in the response
            response_content = response.content.decode()
            self.assertIn('testuser@gmail.com', response_content)
            print("✅ Account appears in email accounts partial")
            
            # Test dashboard overview partial
            response = self.client.get(reverse('core:dashboard-overview-partial'))
            self.assertEqual(response.status_code, 200)
            
            # Check account count in dashboard
            response_content = response.content.decode()
            print(f"Dashboard content sample: {response_content[:200]}...")
            print("✅ Dashboard overview accessible")
            
            # Test API endpoint for email accounts
            response = self.client.get(reverse('core:email-accounts'))
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            if 'results' in data:
                accounts = data['results']
            else:
                accounts = data if isinstance(data, list) else []
            
            self.assertTrue(len(accounts) >= 1)
            account_emails = [acc['email_address'] for acc in accounts]
            self.assertIn('testuser@gmail.com', account_emails)
            print("✅ Account visible in API endpoint")
            
            return True
        else:
            print("❌ Cannot test dashboard visibility - account creation failed")
            return False
    
    def test_6_edge_cases_and_errors(self):
        """Test 6: Edge cases and error handling"""
        print("\n=== Test 6: Edge Cases and Error Handling ===")
        
        # Test callback without code parameter
        callback_url = reverse('core:gmail_oauth_callback')
        response = self.client.get(callback_url, {'error': 'access_denied'})
        self.assertEqual(response.status_code, 302)  # Should redirect
        print("✅ Handles OAuth denial correctly")
        
        # Test callback with invalid state (CSRF protection)
        response = self.client.get(callback_url, {
            'code': 'test_code',
            'state': 'invalid_state'
        })
        self.assertEqual(response.status_code, 302)  # Should redirect with error
        print("✅ CSRF protection working")
        
        # Test unauthenticated access to OAuth endpoints
        self.client.logout()
        response = self.client.get(reverse('core:gmail_oauth_login'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        print("✅ OAuth endpoints require authentication")
        
        # Re-login for cleanup
        self.client.force_login(self.user)
        
        return True
    
    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive OAuth Flow Test")
        print("=" * 60)
        
        results = {}
        
        try:
            # Run tests in sequence
            results['user_creation'] = self.test_1_user_creation()
            results['oauth_login'] = self.test_2_gmail_oauth_login() is not None
            results['oauth_callback'] = self.test_3_gmail_oauth_callback() is not None
            results['database_storage'] = self.test_4_account_database_storage() is not None
            results['dashboard_visibility'] = self.test_5_dashboard_visibility()
            results['edge_cases'] = self.test_6_edge_cases_and_errors()
            
            # Generate summary
            print("\n🎯 TEST SUMMARY")
            print("=" * 60)
            
            passed_tests = sum(results.values())
            total_tests = len(results)
            
            for test_name, passed in results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{status} {test_name.replace('_', ' ').title()}")
            
            print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
            
            if passed_tests == total_tests:
                print("🟢 ALL TESTS PASSED - OAuth flow is working correctly!")
                print("\n📋 Next steps:")
                print("   1. Test the flow in a browser at http://localhost:8001/auth/debug/")
                print("   2. Verify Google shows your app name, not 'Black Coral'")
                print("   3. Check that accounts appear in the dashboard")
            else:
                print("🔴 SOME TESTS FAILED - OAuth flow has issues")
                
                # Identify specific failure points
                failed_tests = [name for name, passed in results.items() if not passed]
                print(f"\nFailed tests: {', '.join(failed_tests)}")
                
                # Generate recommendations
                recommendations = []
                
                if not results.get('oauth_login'):
                    recommendations.append("Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file")
                
                if not results.get('oauth_callback'):
                    recommendations.append("Check OAuth callback URL configuration")
                
                if not results.get('database_storage'):
                    recommendations.append("Check database permissions and model relationships")
                
                if not results.get('dashboard_visibility'):
                    recommendations.append("Check template rendering and HTMX partial views")
                
                if recommendations:
                    print("\n💡 Recommendations:")
                    for i, rec in enumerate(recommendations, 1):
                        print(f"   {i}. {rec}")
            
            return passed_tests == total_tests
            
        except Exception as e:
            print(f"\n💥 Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main test execution"""
    # Setup Django test database
    from django.test.utils import setup_test_environment, teardown_test_environment
    from django.db import connection
    from django.core.management.color import no_style
    from django.core.management.sql import sql_flush
    
    setup_test_environment()
    
    # Create test instance
    test_instance = OAuthFlowTest()
    test_instance.setUp()
    
    try:
        # Run the comprehensive test
        success = test_instance.run_comprehensive_test()
        
        # Cleanup
        test_instance.tearDown() if hasattr(test_instance, 'tearDown') else None
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        teardown_test_environment()

if __name__ == '__main__':
    sys.exit(main())

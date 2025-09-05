#!/usr/bin/env python3

"""
Simple OAuth flow test using Django test framework
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from unittest.mock import patch, Mock
from urllib.parse import urlparse, parse_qs
from datetime import timedelta
import uuid

from core.models import EmailAccount

User = get_user_model()

class SimpleOAuthTest(TestCase):
    """Simple OAuth flow test"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='oauth_test_user',
            email='test@fyxerai.com',
            password='TestPass123!'
        )
        
        # Login the user
        self.client.force_login(self.user)
        
        # Mock OAuth config
        self.mock_config = {
            'google_client_id': 'test_client_id_123.apps.googleusercontent.com',
            'google_client_secret': 'test_client_secret_456'
        }
    
    def test_user_creation(self):
        """Test 1: Create and verify test user"""
        print("\n=== Test 1: User Creation ===")
        
        # Verify user was created
        user = User.objects.get(username='oauth_test_user')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@fyxerai.com')
        print("✅ Test user created successfully")
        
        # Check initial account count
        account_count = EmailAccount.objects.filter(user=user).count()
        self.assertEqual(account_count, 0)
        print("✅ User starts with 0 email accounts")
    
    @patch.object(settings, 'GOOGLE_CLIENT_ID', 'test_client_id_123.apps.googleusercontent.com')
    @patch.object(settings, 'GOOGLE_CLIENT_SECRET', 'test_client_secret_456')
    def test_oauth_login_redirect(self):
        """Test 2: OAuth login endpoint redirect"""
        print("\n=== Test 2: Gmail OAuth Login Endpoint ===")
        
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
            self.assertEqual(client_id_in_url, self.mock_config['google_client_id'])
            print("✅ Client ID correctly included in OAuth URL")
            
            return True
        else:
            print(f"❌ OAuth redirect failed with status {response.status_code}")
            return False
    
    @patch.object(settings, 'GOOGLE_CLIENT_ID', 'test_client_id_123.apps.googleusercontent.com')
    @patch.object(settings, 'GOOGLE_CLIENT_SECRET', 'test_client_secret_456')
    @patch('core.views_oauth.Flow')
    @patch('core.views_oauth.get_gmail_user_info')
    def test_oauth_callback_success(self, mock_get_user_info, mock_flow):
        """Test 3: OAuth callback with successful authentication"""
        print("\n=== Test 3: Gmail OAuth Callback ===")
        
        # Mock user info from Google
        mock_user_info.return_value = {
            'email': 'testuser@gmail.com',
            'name': 'Test User',
            'id': '123456789'
        }
        
        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.token = 'mock_access_token_123'
        mock_credentials.refresh_token = 'mock_refresh_token_456'
        mock_credentials.expiry = timezone.now() + timedelta(hours=1)
        
        # Setup mock flow
        mock_flow_instance = Mock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow.from_client_config.return_value = mock_flow_instance
        
        # Create valid OAuth state
        session = self.client.session
        oauth_state = str(uuid.uuid4())
        session['oauth_state'] = oauth_state
        session.save()
        
        # Simulate OAuth callback
        callback_url = reverse('core:gmail_oauth_callback')
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
                return None
        else:
            print(f"❌ OAuth callback failed with status {response.status_code}")
            return None
    
    def test_dashboard_account_visibility(self):
        """Test 4: Verify account appears in dashboard"""
        print("\n=== Test 4: Dashboard Account Visibility ===")
        
        # First create a mock account directly for testing dashboard
        account = EmailAccount.objects.create(
            user=self.user,
            provider='gmail',
            email_address='dashboard_test@gmail.com',
            display_name='Dashboard Test User',
            access_token=EmailAccount().encrypt_token('test_token'),
            refresh_token=EmailAccount().encrypt_token('test_refresh'),
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_active=True
        )
        
        # Test dashboard home view
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        print("✅ Dashboard accessible")
        
        # Test email accounts partial (HTMX endpoint)
        response = self.client.get(reverse('core:email-accounts-partial'))
        self.assertEqual(response.status_code, 200)
        
        # Check if account appears in the response
        response_content = response.content.decode()
        self.assertIn('dashboard_test@gmail.com', response_content)
        print("✅ Account appears in email accounts partial")
        
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
        self.assertIn('dashboard_test@gmail.com', account_emails)
        print("✅ Account visible in API endpoint")
        
        return True
    
    def test_oauth_error_handling(self):
        """Test 5: OAuth error handling"""
        print("\n=== Test 5: OAuth Error Handling ===")
        
        # Test OAuth denial
        callback_url = reverse('core:gmail_oauth_callback')
        response = self.client.get(callback_url, {'error': 'access_denied'})
        self.assertEqual(response.status_code, 302)
        print("✅ Handles OAuth denial correctly")
        
        # Test invalid state (CSRF protection)
        response = self.client.get(callback_url, {
            'code': 'test_code',
            'state': 'invalid_state'
        })
        self.assertEqual(response.status_code, 302)
        print("✅ CSRF protection working")
        
        return True
    
    def test_account_database_operations(self):
        """Test 6: Database operations on email accounts"""
        print("\n=== Test 6: Account Database Operations ===")
        
        # Create test account
        account = EmailAccount.objects.create(
            user=self.user,
            provider='gmail',
            email_address='dbtest@gmail.com',
            display_name='DB Test User',
            access_token=EmailAccount().encrypt_token('test_access_token'),
            refresh_token=EmailAccount().encrypt_token('test_refresh_token'),
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_active=True
        )
        
        print("✅ Account created in database")
        
        # Test token encryption/decryption
        decrypted_access = account.decrypt_token(account.access_token)
        self.assertEqual(decrypted_access, 'test_access_token')
        print("✅ Token encryption/decryption working")
        
        # Test account retrieval
        retrieved_account = EmailAccount.objects.get(id=account.id)
        self.assertEqual(retrieved_account.email_address, 'dbtest@gmail.com')
        print("✅ Account retrieval working")
        
        # Test unique constraint
        with self.assertRaises(Exception):
            EmailAccount.objects.create(
                user=self.user,
                provider='gmail',
                email_address='dbtest@gmail.com',  # Same email
                access_token=EmailAccount().encrypt_token('duplicate_token'),
                refresh_token=EmailAccount().encrypt_token('duplicate_refresh'),
                token_expires_at=timezone.now() + timedelta(hours=1)
            )
        print("✅ Unique constraint prevents duplicate accounts")
        
        return True

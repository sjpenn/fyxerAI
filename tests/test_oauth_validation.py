#!/usr/bin/env python3

"""
Django-based OAuth validation test
Tests OAuth configuration and flow without browser automation
"""

import os
import sys
import json
from datetime import datetime
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
from core.models import EmailAccount

User = get_user_model()

class OAuthValidationTest:
    """Validation test for OAuth configuration"""
    
    def __init__(self):
        self.client = Client()
        self.user = None
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'test_results': {},
            'configuration_check': {},
            'recommendations': []
        }
        
    def setup_test_user(self):
        """Create a test user for OAuth testing"""
        print("👤 Setting up test user...")
        
        # Clean up existing test users
        User.objects.filter(username='oauth_test_user').delete()
        User.objects.filter(email='test@fyxerai.com').delete()
        
        # Create new test user
        self.user = User.objects.create_user(
            username='oauth_test_user',
            email='test@fyxerai.com',
            password='TestPass123!'
        )
        
        # Login the user
        login_success = self.client.login(username='oauth_test_user', password='TestPass123!')
        
        if login_success:
            print("✅ Test user created and logged in")
            return True
        else:
            print("❌ Failed to login test user")
            return False
            
    def check_oauth_configuration(self):
        """Check OAuth configuration in settings"""
        print("\n🔧 Checking OAuth Configuration...")
        
        config_check = {
            'google_client_id_configured': bool(settings.GOOGLE_CLIENT_ID),
            'google_client_secret_configured': bool(settings.GOOGLE_CLIENT_SECRET),
            'google_client_id_value': settings.GOOGLE_CLIENT_ID[:20] + '...' if settings.GOOGLE_CLIENT_ID else 'Not set',
            'base_url': getattr(settings, 'BASE_URL', 'http://localhost:8000')
        }
        
        self.report['configuration_check'] = config_check
        
        for key, value in config_check.items():
            status = '✅' if value else '❌'
            print(f"   {status} {key}: {value}")
            
        return all([
            config_check['google_client_id_configured'],
            config_check['google_client_secret_configured']
        ])
        
    def test_debug_page(self):
        """Test the OAuth debug page"""
        print("\n📊 Testing OAuth Debug Page...")
        
        try:
            response = self.client.get('/auth/debug/')
            
            if response.status_code == 200:
                print("✅ Debug page accessible")
                
                # Check for Black Coral references
                page_content = response.content.decode('utf-8')
                contains_black_coral = 'black coral' in page_content.lower()
                
                if contains_black_coral:
                    print("⚠️  WARNING: 'Black Coral' references found in debug page")
                    print("   This is expected in the template warning message")
                else:
                    print("✅ No 'Black Coral' references found")
                    
                self.report['test_results']['debug_page'] = {
                    'accessible': True,
                    'contains_black_coral_warning': contains_black_coral,
                    'status_code': response.status_code
                }
                
                return True
            else:
                print(f"❌ Debug page returned status {response.status_code}")
                self.report['test_results']['debug_page'] = {
                    'accessible': False,
                    'status_code': response.status_code
                }
                return False
                
        except Exception as e:
            print(f"❌ Debug page test failed: {str(e)}")
            self.report['test_results']['debug_page'] = {
                'accessible': False,
                'error': str(e)
            }
            return False
            
    def test_oauth_redirect(self):
        """Test the OAuth login redirect"""
        print("\n🔐 Testing OAuth Login Redirect...")
        
        try:
            response = self.client.get('/auth/gmail/login/', follow=False)
            
            if response.status_code == 302:
                redirect_url = response.get('Location', '')
                print(f"✅ OAuth redirect working (status: {response.status_code})")
                print(f"📍 Redirect URL: {redirect_url[:100]}...")
                
                # Parse the redirect URL to analyze it
                parsed_url = urlparse(redirect_url)
                query_params = parse_qs(parsed_url.query)
                
                # Check if it's going to Google OAuth
                is_google_oauth = 'accounts.google.com' in redirect_url
                
                result = {
                    'redirect_working': True,
                    'status_code': response.status_code,
                    'redirect_url': redirect_url,
                    'is_google_oauth': is_google_oauth,
                    'client_id_in_url': settings.GOOGLE_CLIENT_ID in redirect_url if settings.GOOGLE_CLIENT_ID else False
                }
                
                if is_google_oauth:
                    print("✅ Correctly redirecting to Google OAuth")
                    
                    # Extract client_id from URL to verify
                    client_id_param = query_params.get('client_id', [''])[0]
                    if client_id_param and settings.GOOGLE_CLIENT_ID:
                        if client_id_param == settings.GOOGLE_CLIENT_ID:
                            print("✅ Client ID in URL matches configuration")
                            result['client_id_match'] = True
                        else:
                            print("⚠️  Client ID in URL doesn't match configuration")
                            print(f"   URL: {client_id_param[:20]}...")
                            print(f"   Config: {settings.GOOGLE_CLIENT_ID[:20]}...")
                            result['client_id_match'] = False
                    
                    # Check callback URL
                    redirect_uri = query_params.get('redirect_uri', [''])[0]
                    if redirect_uri:
                        print(f"📍 Callback URL: {redirect_uri}")
                        result['callback_url'] = redirect_uri
                        
                else:
                    print("❌ Not redirecting to Google OAuth")
                    
                self.report['test_results']['oauth_redirect'] = result
                return is_google_oauth
                
            else:
                print(f"❌ OAuth redirect failed (status: {response.status_code})")
                
                if response.status_code == 500:
                    print("   This might indicate a configuration error")
                    
                self.report['test_results']['oauth_redirect'] = {
                    'redirect_working': False,
                    'status_code': response.status_code
                }
                return False
                
        except Exception as e:
            print(f"❌ OAuth redirect test failed: {str(e)}")
            self.report['test_results']['oauth_redirect'] = {
                'redirect_working': False,
                'error': str(e)
            }
            return False
            
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        print("\n💡 Generating Recommendations...")
        
        config_check = self.report['configuration_check']
        oauth_redirect = self.report['test_results'].get('oauth_redirect', {})
        
        if not config_check.get('google_client_id_configured'):
            self.report['recommendations'].append(
                "Set GOOGLE_CLIENT_ID in your .env file"
            )
            
        if not config_check.get('google_client_secret_configured'):
            self.report['recommendations'].append(
                "Set GOOGLE_CLIENT_SECRET in your .env file"
            )
            
        if oauth_redirect.get('is_google_oauth') and oauth_redirect.get('client_id_match') is False:
            self.report['recommendations'].append(
                "Client ID in OAuth URL doesn't match configuration - check your .env file"
            )
            
        if oauth_redirect.get('is_google_oauth'):
            self.report['recommendations'].append(
                "OAuth redirect is working - test the flow in a browser to check for 'Black Coral' references"
            )
            self.report['recommendations'].append(
                "Visit Google Cloud Console to verify your OAuth app name: https://console.cloud.google.com/apis/credentials"
            )
            
        if not self.report['recommendations']:
            self.report['recommendations'].append(
                "OAuth configuration appears to be working correctly"
            )
            
        for i, rec in enumerate(self.report['recommendations'], 1):
            print(f"   {i}. {rec}")
            
    def save_report(self):
        """Save the test report"""
        report_path = 'oauth_validation_report.json'
        with open(report_path, 'w') as f:
            json.dump(self.report, f, indent=2)
        print(f"\n📄 Report saved: {report_path}")
        
    def run_validation(self):
        """Run the complete OAuth validation"""
        print("🚀 Starting OAuth Validation Test...")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_user():
            return False
            
        # Run tests
        config_ok = self.check_oauth_configuration()
        debug_page_ok = self.test_debug_page()
        oauth_redirect_ok = self.test_oauth_redirect() if config_ok else False
        
        # Generate recommendations
        self.generate_recommendations()
        
        # Save report
        self.save_report()
        
        # Summary
        print("\n🎯 VALIDATION SUMMARY:")
        print("=" * 60)
        
        overall_status = all([config_ok, debug_page_ok, oauth_redirect_ok])
        
        if overall_status:
            print("🟢 OAuth configuration appears to be working correctly")
            print("📋 Next step: Test the actual OAuth flow in a browser")
            print("   Visit: http://localhost:8001/auth/debug/")
            print("   Click 'Test Gmail OAuth' to see if Google shows 'Black Coral' or 'FYXERAI'")
        else:
            print("🔴 OAuth configuration has issues that need to be resolved")
            
        return overall_status
        
    def cleanup(self):
        """Clean up test data"""
        if self.user:
            self.user.delete()
            print("🧹 Test user cleaned up")

if __name__ == '__main__':
    validator = OAuthValidationTest()
    try:
        success = validator.run_validation()
        exit_code = 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        exit_code = 1
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        exit_code = 1
    finally:
        validator.cleanup()
        
    sys.exit(exit_code)
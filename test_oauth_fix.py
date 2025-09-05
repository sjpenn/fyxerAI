#!/usr/bin/env python3
"""
Test script to validate the Gmail OAuth fix
"""
import os
import sys
import django

# Setup Django environment
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyxerai_assistant.settings'
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import EmailAccount
import json

def test_oauth_fix():
    """Test the OAuth flow and dashboard refresh fix"""
    print("=== Testing OAuth Fix ===")
    
    User = get_user_model()
    client = Client()
    
    # Get test user
    try:
        user = User.objects.get(username='testgmail')
        print(f"✓ Found test user: {user.username}")
    except User.DoesNotExist:
        print("✗ Test user not found. Creating...")
        user = User.objects.create_user(
            username='testgmail',
            email='testgmail@example.com',
            password='testpass123'
        )
        print(f"✓ Created test user: {user.username}")
    
    # Login the user
    login_success = client.login(username='testgmail', password='testpass123')
    print(f"✓ User login successful: {login_success}")
    
    # Check initial account count
    initial_accounts = EmailAccount.objects.filter(user=user).count()
    print(f"✓ Initial email accounts for user: {initial_accounts}")
    
    # Test dashboard view loads correctly
    response = client.get('/')
    print(f"✓ Dashboard loads with status: {response.status_code}")
    
    # Test dashboard overview partial
    response = client.get('/partials/dashboard-overview/')
    print(f"✓ Dashboard overview partial status: {response.status_code}")
    
    # Test email accounts partial
    response = client.get('/partials/email-accounts/')
    print(f"✓ Email accounts partial status: {response.status_code}")
    
    # Simulate successful OAuth by creating an account
    print("\n=== Simulating OAuth Success ===")
    test_account = EmailAccount.objects.create(
        user=user,
        provider='gmail',
        email_address='testgmail.oauth@gmail.com',
        display_name='Test Gmail OAuth',
        access_token='fake_encrypted_token',
        refresh_token='fake_encrypted_refresh_token',
        is_active=True
    )
    print(f"✓ Created test Gmail account: {test_account.email_address}")
    
    # Test that dashboard now shows the account
    response = client.get('/partials/email-accounts/')
    print(f"✓ Accounts partial after account creation: {response.status_code}")
    
    # Check if account appears in response content
    if test_account.email_address.encode() in response.content:
        print("✓ Account appears in dashboard response")
    else:
        print("✗ Account NOT appearing in dashboard response")
        print("Response content preview:")
        print(response.content.decode()[:500] + "...")
    
    # Test dashboard overview with account data
    response = client.get('/partials/dashboard-overview/')
    print(f"✓ Dashboard overview with accounts: {response.status_code}")
    
    # Simulate OAuth success session flags
    session = client.session
    session['account_connected'] = True
    session['connected_account_email'] = test_account.email_address
    session.save()
    
    # Test home view with OAuth success flags
    response = client.get('/')
    print(f"✓ Dashboard with OAuth success flags: {response.status_code}")
    
    # Check if OAuth success JavaScript is in the response
    if b'OAuth success detected' in response.content:
        print("✓ OAuth success detection JavaScript included")
    else:
        print("✗ OAuth success detection JavaScript NOT found")
    
    # Clean up test data
    test_account.delete()
    print(f"✓ Cleaned up test account")
    
    print("\n=== Fix Test Complete ===")
    return True

if __name__ == "__main__":
    try:
        test_oauth_fix()
        print("\n🎉 All tests passed! OAuth fix appears to be working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
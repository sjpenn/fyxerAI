#!/usr/bin/env python3
"""
Quick OAuth Status Check
Run this to verify OAuth backend health and account status
"""
import os
import sys

# Fix Django settings if needed
if 'DJANGO_SETTINGS_MODULE' in os.environ and 'blackcoral' in os.environ['DJANGO_SETTINGS_MODULE']:
    del os.environ['DJANGO_SETTINGS_MODULE']

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fyxerai_assistant.settings')
os.environ.setdefault('USE_DOTENV', '0')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import django
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import EmailAccount

def quick_check():
    """Quick OAuth backend health check"""
    print("🔍 Quick OAuth Backend Check")
    print("-" * 40)
    
    # Check configuration
    print(f"Google Client ID: {'✅' if settings.GOOGLE_CLIENT_ID else '❌'}")
    print(f"Google Client Secret: {'✅' if settings.GOOGLE_CLIENT_SECRET else '❌'}")
    
    # Check users and accounts
    User = get_user_model()
    user_count = User.objects.count()
    account_count = EmailAccount.objects.count()
    
    print(f"Total users: {user_count}")
    print(f"Total email accounts: {account_count}")
    
    # Show recent accounts
    if account_count > 0:
        print("\n📧 Recent Email Accounts:")
        recent_accounts = EmailAccount.objects.order_by('-created_at')[:5]
        for account in recent_accounts:
            print(f"   {account.email_address} ({account.provider}) - {'Active' if account.is_active else 'Inactive'}")
    
    print(f"\n🔗 OAuth URLs:")
    print(f"   Debug: http://localhost:8001/auth/debug/")
    print(f"   Login: http://localhost:8001/auth/gmail/login/")
    print(f"   Dashboard: http://localhost:8001/")

if __name__ == '__main__':
    try:
        quick_check()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

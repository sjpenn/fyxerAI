"""
Django management command to debug OAuth flow and account connectivity issues.

Usage:
    python manage.py debug_oauth_flow --user <user_id>
    python manage.py debug_oauth_flow --email <email>
    python manage.py debug_oauth_flow --all
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import EmailAccount
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Debug OAuth flow and account connectivity issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=int,
            help='Debug specific user ID',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Debug specific user email',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Debug all users',
        )
        parser.add_argument(
            '--fix-tokens',
            action='store_true',
            help='Attempt to fix expired tokens',
        )
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        # Determine which users to debug
        users_to_debug = []
        
        if options['user']:
            try:
                user = User.objects.get(id=options['user'])
                users_to_debug = [user]
            except User.DoesNotExist:
                raise CommandError(f'User with ID {options["user"]} does not exist')
        elif options['email']:
            try:
                user = User.objects.get(email=options['email'])
                users_to_debug = [user]
            except User.DoesNotExist:
                raise CommandError(f'User with email {options["email"]} does not exist')
        elif options['all']:
            users_to_debug = User.objects.all()
        else:
            raise CommandError('Must specify --user, --email, or --all')
        
        # Debug OAuth configuration
        self.debug_oauth_config()
        
        # Debug each user
        for user in users_to_debug:
            self.debug_user(user, options.get('fix_tokens', False))
    
    def debug_oauth_config(self):
        """Debug OAuth configuration settings"""
        self.stdout.write(self.style.SUCCESS('=== OAuth Configuration Debug ==='))
        
        # Check Google OAuth settings
        google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        google_client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', None)
        
        self.stdout.write(f'Google Client ID configured: {"Yes" if google_client_id else "No"}')
        if google_client_id:
            self.stdout.write(f'Google Client ID: {google_client_id[:20]}...')
        
        self.stdout.write(f'Google Client Secret configured: {"Yes" if google_client_secret else "No"}')
        
        # Check base URL
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        self.stdout.write(f'Base URL: {base_url}')
        
        # Check callback URL
        callback_url = f'{base_url}/auth/gmail/callback/'
        self.stdout.write(f'Gmail Callback URL: {callback_url}')
        
        self.stdout.write('')
    
    def debug_user(self, user, fix_tokens=False):
        """Debug specific user's OAuth accounts"""
        self.stdout.write(self.style.SUCCESS(f'=== User Debug: {user.username} (ID: {user.id}) ==='))
        
        # Get user's email accounts
        accounts = EmailAccount.objects.filter(user=user)
        
        self.stdout.write(f'Total accounts: {accounts.count()}')
        
        if not accounts.exists():
            self.stdout.write(self.style.WARNING('No email accounts found for this user'))
            return
        
        # Debug each account
        for account in accounts:
            self.debug_account(account, fix_tokens)
        
        self.stdout.write('')
    
    def debug_account(self, account, fix_tokens=False):
        """Debug specific email account"""
        self.stdout.write(f'--- Account: {account.email_address} ---')
        self.stdout.write(f'Provider: {account.get_provider_display()}')
        self.stdout.write(f'Display Name: {account.display_name}')
        self.stdout.write(f'Active: {account.is_active}')
        self.stdout.write(f'Created: {account.created_at}')
        self.stdout.write(f'Last Sync: {account.last_sync or "Never"}')
        
        # Check token expiry
        if account.token_expires_at:
            now = timezone.now()
            if account.token_expires_at < now:
                self.stdout.write(self.style.ERROR(f'Token expired: {account.token_expires_at}'))
                if fix_tokens:
                    self.stdout.write('Attempting to refresh token...')
                    if self.refresh_account_token(account):
                        self.stdout.write(self.style.SUCCESS('Token refreshed successfully'))
                    else:
                        self.stdout.write(self.style.ERROR('Token refresh failed'))
            else:
                expires_in = account.token_expires_at - now
                self.stdout.write(f'Token expires in: {expires_in}')
        else:
            self.stdout.write(self.style.WARNING('No token expiry set'))
        
        # Test token validity
        if account.provider == 'gmail':
            self.test_gmail_token(account)
        
        self.stdout.write('')
    
    def refresh_account_token(self, account):
        """Attempt to refresh account token"""
        if account.provider == 'gmail':
            from core.views_oauth import refresh_gmail_token
            return refresh_gmail_token(account)
        return False
    
    def test_gmail_token(self, account):
        """Test Gmail token validity"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            # Decrypt tokens
            access_token = account.decrypt_token(account.access_token)
            refresh_token = account.decrypt_token(account.refresh_token)
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )
            
            # Try to make a simple API call
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            
            self.stdout.write(self.style.SUCCESS(f'Gmail API test successful: {profile.get("emailAddress")}'))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Gmail API test failed: {str(e)}'))
            return False
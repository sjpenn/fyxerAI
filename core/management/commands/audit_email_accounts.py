from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from core.models import User, EmailAccount
from tabulate import tabulate
import json


class Command(BaseCommand):
    help = 'Audit EmailAccount entries in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information including encrypted tokens',
        )
        parser.add_argument(
            '--inactive-only',
            action='store_true',
            help='Show only inactive accounts',
        )
        parser.add_argument(
            '--duplicates',
            action='store_true',
            help='Show potential duplicate accounts',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== EmailAccount Database Audit ===\n')
        )

        # Basic statistics
        total_accounts = EmailAccount.objects.count()
        total_users = User.objects.count()
        active_accounts = EmailAccount.objects.filter(is_active=True).count()
        inactive_accounts = EmailAccount.objects.filter(is_active=False).count()
        gmail_accounts = EmailAccount.objects.filter(provider='gmail').count()
        outlook_accounts = EmailAccount.objects.filter(provider='outlook').count()

        self.stdout.write(f"📊 Database Statistics:")
        self.stdout.write(f"   • Total Users: {total_users}")
        self.stdout.write(f"   • Total Email Accounts: {total_accounts}")
        self.stdout.write(f"   • Active Accounts: {active_accounts}")
        self.stdout.write(f"   • Inactive Accounts: {inactive_accounts}")
        self.stdout.write(f"   • Gmail Accounts: {gmail_accounts}")
        self.stdout.write(f"   • Outlook Accounts: {outlook_accounts}")
        self.stdout.write("")

        # Get accounts to display
        if options['inactive_only']:
            accounts = EmailAccount.objects.filter(is_active=False).select_related('user')
            self.stdout.write(self.style.WARNING("🔍 Showing INACTIVE accounts only:\n"))
        else:
            accounts = EmailAccount.objects.all().select_related('user')
            self.stdout.write("📋 All Email Accounts:\n")

        if not accounts.exists():
            self.stdout.write(self.style.WARNING("No email accounts found in database."))
            return

        # Prepare table data
        table_data = []
        for account in accounts:
            # Check for potential issues
            issues = []
            if not account.is_active:
                issues.append("INACTIVE")
            if not account.sync_enabled:
                issues.append("SYNC_DISABLED")
            if account.token_expires_at and account.token_expires_at < timezone.now():
                issues.append("TOKEN_EXPIRED")
            if not account.access_token.strip():
                issues.append("NO_ACCESS_TOKEN")
            if not account.refresh_token.strip():
                issues.append("NO_REFRESH_TOKEN")

            issues_str = ", ".join(issues) if issues else "✓"

            table_data.append([
                account.id,
                account.user.username,
                account.provider.upper(),
                account.email_address,
                account.display_name[:30] + "..." if len(account.display_name) > 30 else account.display_name,
                "✓" if account.is_active else "✗",
                "✓" if account.sync_enabled else "✗",
                account.last_sync.strftime("%Y-%m-%d %H:%M") if account.last_sync else "Never",
                account.created_at.strftime("%Y-%m-%d"),
                issues_str
            ])

        headers = [
            "ID", "User", "Provider", "Email", "Display Name", 
            "Active", "Sync", "Last Sync", "Created", "Issues"
        ]

        self.stdout.write(tabulate(table_data, headers=headers, tablefmt="grid"))
        self.stdout.write("")

        # Check for duplicates
        if options['duplicates'] or not options['inactive_only']:
            self.stdout.write("🔍 Checking for duplicate accounts:\n")
            
            # Find duplicate email addresses
            from django.db.models import Count
            duplicates = (EmailAccount.objects
                         .values('email_address', 'provider')
                         .annotate(count=Count('id'))
                         .filter(count__gt=1))
            
            if duplicates:
                self.stdout.write(self.style.WARNING("⚠️  Found potential duplicates:"))
                for dup in duplicates:
                    dup_accounts = EmailAccount.objects.filter(
                        email_address=dup['email_address'],
                        provider=dup['provider']
                    ).select_related('user')
                    
                    self.stdout.write(f"   • {dup['email_address']} ({dup['provider']}): {dup['count']} accounts")
                    for acc in dup_accounts:
                        status = "ACTIVE" if acc.is_active else "INACTIVE"
                        self.stdout.write(f"     - ID {acc.id}, User: {acc.user.username}, Status: {status}")
                self.stdout.write("")
            else:
                self.stdout.write("✅ No duplicate accounts found.\n")

        # Check for orphaned accounts (users with no email accounts)
        users_without_accounts = User.objects.filter(email_accounts__isnull=True)
        if users_without_accounts.exists():
            self.stdout.write(self.style.WARNING("👤 Users without email accounts:"))
            for user in users_without_accounts:
                self.stdout.write(f"   • {user.username} (ID: {user.id})")
            self.stdout.write("")
        else:
            self.stdout.write("✅ All users have at least one email account.\n")

        # Detailed token information if requested
        if options['detailed']:
            self.stdout.write("🔐 Detailed Token Information:\n")
            for account in accounts[:5]:  # Limit to first 5 for security
                self.stdout.write(f"Account ID {account.id} ({account.email_address}):")
                self.stdout.write(f"   • Access Token Length: {len(account.access_token)} chars")
                self.stdout.write(f"   • Refresh Token Length: {len(account.refresh_token)} chars")
                self.stdout.write(f"   • Token Expires: {account.token_expires_at}")
                try:
                    # Try to decrypt just to verify tokens are properly encrypted
                    decrypted_access = account.decrypt_token(account.access_token)
                    decrypted_refresh = account.decrypt_token(account.refresh_token)
                    self.stdout.write("   • Token Encryption: ✅ Valid")
                except Exception as e:
                    self.stdout.write(f"   • Token Encryption: ❌ Error - {str(e)}")
                self.stdout.write("")

        # Summary and recommendations
        self.stdout.write("📝 Summary & Recommendations:\n")
        
        if inactive_accounts > 0:
            self.stdout.write(f"⚠️  {inactive_accounts} inactive accounts found. Consider:")
            self.stdout.write("   • Re-authenticating inactive Gmail accounts")
            self.stdout.write("   • Removing permanently disconnected accounts")
        
        expired_tokens = EmailAccount.objects.filter(
            token_expires_at__lt=timezone.now()
        ).count()
        if expired_tokens > 0:
            self.stdout.write(f"⚠️  {expired_tokens} accounts with expired tokens")
            self.stdout.write("   • These need token refresh or re-authentication")
        
        never_synced = EmailAccount.objects.filter(last_sync__isnull=True).count()
        if never_synced > 0:
            self.stdout.write(f"⚠️  {never_synced} accounts never synced")
            self.stdout.write("   • Check sync service functionality")

        self.stdout.write("\n" + "="*50)
        self.stdout.write("Audit completed successfully!")
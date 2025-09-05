from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.models import EmailAccount, EmailMessage, UserPreference, Meeting
from datetime import timedelta
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Comprehensive database health check and operational status report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--export-json',
            action='store_true',
            help='Export findings as JSON for monitoring systems',
        )

    def handle(self, *args, **options):
        findings = {
            'timestamp': timezone.now().isoformat(),
            'database_stats': {},
            'account_health': {},
            'data_integrity': {},
            'operational_issues': [],
            'recommendations': []
        }

        self.stdout.write(
            self.style.SUCCESS('=== Database Health Check & Operational Status ===\n')
        )

        # Database Statistics
        findings['database_stats'] = self._check_database_stats()
        self._print_database_stats(findings['database_stats'])

        # Account Health
        findings['account_health'] = self._check_account_health()
        self._print_account_health(findings['account_health'])

        # Data Integrity
        findings['data_integrity'] = self._check_data_integrity()
        self._print_data_integrity(findings['data_integrity'])

        # Operational Issues
        findings['operational_issues'] = self._identify_operational_issues()
        findings['recommendations'] = self._generate_recommendations(findings)
        self._print_operational_status(findings)

        # Export JSON if requested
        if options['export_json']:
            self._export_json(findings)

        self.stdout.write(
            self.style.SUCCESS('\n=== Health Check Complete ===')
        )

    def _check_database_stats(self):
        stats = {}
        
        # Core model counts
        stats['users'] = {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'with_accounts': User.objects.filter(email_accounts__isnull=False).distinct().count()
        }
        
        stats['email_accounts'] = {
            'total': EmailAccount.objects.count(),
            'active': EmailAccount.objects.filter(is_active=True).count(),
            'gmail': EmailAccount.objects.filter(provider='gmail').count(),
            'outlook': EmailAccount.objects.filter(provider='outlook').count()
        }
        
        stats['messages'] = {
            'total': EmailMessage.objects.count(),
            'last_24h': EmailMessage.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count(),
            'unread': EmailMessage.objects.filter(is_read=False).count(),
            'with_drafts': EmailMessage.objects.filter(has_draft_reply=True).count()
        }
        
        stats['preferences'] = {
            'configured': UserPreference.objects.count(),
            'auto_categorize_enabled': UserPreference.objects.filter(auto_categorize=True).count()
        }
        
        stats['meetings'] = {
            'total': Meeting.objects.count(),
            'completed': Meeting.objects.filter(status='completed').count(),
            'with_transcripts': Meeting.objects.filter(has_transcript=True).count()
        }
        
        # Database size info
        with connection.cursor() as cursor:
            if 'sqlite' in connection.vendor:
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();")
                db_size = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
                stats['database_size_bytes'] = db_size
            else:
                stats['database_size_bytes'] = None
                
        return stats

    def _check_account_health(self):
        health = {}
        current_time = timezone.now()
        
        # Token status
        accounts = EmailAccount.objects.all()
        health['token_status'] = {
            'total_accounts': accounts.count(),
            'valid_tokens': 0,
            'expired_tokens': 0,
            'missing_tokens': 0,
            'dummy_tokens': 0
        }
        
        health['sync_status'] = {
            'sync_enabled': EmailAccount.objects.filter(sync_enabled=True).count(),
            'never_synced': EmailAccount.objects.filter(last_sync__isnull=True).count(),
            'stale_sync': EmailAccount.objects.filter(
                last_sync__lt=current_time - timedelta(hours=24)
            ).count()
        }
        
        for account in accounts:
            # Check token validity
            if not account.access_token or not account.refresh_token:
                health['token_status']['missing_tokens'] += 1
            elif account.access_token == 'dummy_access_token':
                health['token_status']['dummy_tokens'] += 1
            elif account.token_expires_at and account.token_expires_at < current_time:
                health['token_status']['expired_tokens'] += 1
            else:
                health['token_status']['valid_tokens'] += 1
        
        return health

    def _check_data_integrity(self):
        integrity = {}
        
        # Orphaned records
        integrity['orphaned_messages'] = EmailMessage.objects.filter(
            account__isnull=True
        ).count()
        
        # Duplicate accounts
        from django.db.models import Count
        duplicates = (EmailAccount.objects
                     .values('email_address', 'provider')
                     .annotate(count=Count('id'))
                     .filter(count__gt=1))
        integrity['duplicate_accounts'] = len(duplicates)
        
        # Missing user preferences
        users_without_prefs = User.objects.filter(preferences__isnull=True).count()
        integrity['users_without_preferences'] = users_without_prefs
        
        # Message consistency
        integrity['messages_without_accounts'] = EmailMessage.objects.filter(
            account__isnull=True
        ).count()
        
        return integrity

    def _identify_operational_issues(self):
        issues = []
        current_time = timezone.now()
        
        # Critical issues
        if EmailAccount.objects.filter(is_active=True).count() == 0:
            issues.append({
                'severity': 'CRITICAL',
                'category': 'authentication',
                'description': 'No active email accounts configured',
                'impact': 'System cannot sync emails'
            })
        
        expired_count = EmailAccount.objects.filter(
            token_expires_at__lt=current_time,
            is_active=True
        ).count()
        
        if expired_count > 0:
            issues.append({
                'severity': 'HIGH',
                'category': 'authentication',
                'description': f'{expired_count} accounts have expired tokens',
                'impact': 'Email sync will fail for these accounts'
            })
        
        dummy_count = EmailAccount.objects.filter(
            access_token='dummy_access_token'
        ).count()
        
        if dummy_count > 0:
            issues.append({
                'severity': 'HIGH',
                'category': 'configuration',
                'description': f'{dummy_count} accounts using dummy/test tokens',
                'impact': 'These accounts cannot perform real OAuth operations'
            })
        
        # Warning issues
        stale_sync = EmailAccount.objects.filter(
            last_sync__lt=current_time - timedelta(days=1),
            is_active=True
        ).count()
        
        if stale_sync > 0:
            issues.append({
                'severity': 'WARNING',
                'category': 'sync',
                'description': f'{stale_sync} accounts have not synced in 24+ hours',
                'impact': 'Recent emails may be missing'
            })
        
        return issues

    def _generate_recommendations(self, findings):
        recommendations = []
        
        # Authentication recommendations
        if findings['account_health']['token_status']['expired_tokens'] > 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'authentication',
                'action': 'Re-authenticate expired accounts',
                'command': 'python manage.py refresh_oauth_tokens'
            })
        
        if findings['account_health']['token_status']['dummy_tokens'] > 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'configuration',
                'action': 'Set up proper OAuth for dummy accounts',
                'command': 'Navigate to /auth/add-account/ to configure real OAuth'
            })
        
        # Backup recommendations
        if findings['database_stats']['messages']['total'] > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'backup',
                'action': 'Implement regular database backups',
                'command': 'python manage.py backup_database'
            })
        
        # Monitoring recommendations
        if not findings['operational_issues']:
            recommendations.append({
                'priority': 'LOW',
                'category': 'monitoring',
                'action': 'Set up automated health checks',
                'command': 'python manage.py db_health_check --export-json > health.json'
            })
        
        return recommendations

    def _print_database_stats(self, stats):
        self.stdout.write("📊 Database Statistics:")
        self.stdout.write(f"   Users: {stats['users']['total']} total, {stats['users']['active']} active")
        self.stdout.write(f"   Email Accounts: {stats['email_accounts']['total']} total, {stats['email_accounts']['active']} active")
        self.stdout.write(f"   Messages: {stats['messages']['total']} total, {stats['messages']['unread']} unread")
        self.stdout.write(f"   Meetings: {stats['meetings']['total']} total, {stats['meetings']['completed']} completed")
        if stats.get('database_size_bytes'):
            size_mb = stats['database_size_bytes'] / (1024 * 1024)
            self.stdout.write(f"   Database Size: {size_mb:.1f} MB")
        self.stdout.write("")

    def _print_account_health(self, health):
        self.stdout.write("🏥 Account Health:")
        token_status = health['token_status']
        self.stdout.write(f"   Valid Tokens: {token_status['valid_tokens']}")
        self.stdout.write(f"   Expired Tokens: {token_status['expired_tokens']}")
        self.stdout.write(f"   Dummy Tokens: {token_status['dummy_tokens']}")
        
        sync_status = health['sync_status']
        self.stdout.write(f"   Sync Enabled: {sync_status['sync_enabled']}")
        self.stdout.write(f"   Never Synced: {sync_status['never_synced']}")
        self.stdout.write(f"   Stale Sync (24h+): {sync_status['stale_sync']}")
        self.stdout.write("")

    def _print_data_integrity(self, integrity):
        self.stdout.write("🔍 Data Integrity:")
        self.stdout.write(f"   Duplicate Accounts: {integrity['duplicate_accounts']}")
        self.stdout.write(f"   Orphaned Messages: {integrity['orphaned_messages']}")
        self.stdout.write(f"   Users Missing Preferences: {integrity['users_without_preferences']}")
        self.stdout.write("")

    def _print_operational_status(self, findings):
        issues = findings['operational_issues']
        recommendations = findings['recommendations']
        
        self.stdout.write("🚨 Operational Issues:")
        if not issues:
            self.stdout.write("   ✅ No operational issues detected")
        else:
            for issue in issues:
                style = self.style.ERROR if issue['severity'] == 'CRITICAL' else \
                       self.style.WARNING if issue['severity'] == 'HIGH' else \
                       self.style.NOTICE
                self.stdout.write(
                    style(f"   {issue['severity']}: {issue['description']}")
                )
        
        self.stdout.write("")
        self.stdout.write("💡 Recommendations:")
        for rec in recommendations:
            self.stdout.write(f"   {rec['priority']}: {rec['action']}")
            self.stdout.write(f"      Command: {rec['command']}")

    def _export_json(self, findings):
        filename = f"health_check_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(findings, f, indent=2, default=str)
        self.stdout.write(f"\n📄 Health check exported to: {filename}")
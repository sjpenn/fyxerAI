"""
Django management command to test the cross-account email categorization system
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

from core.services.categorization_engine import EmailCategorizationEngine, categorize_emails_batch
from core.services.account_sync import CrossAccountSyncManager
from core.models import EmailAccount, EmailMessage

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the cross-account email categorization system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of the user to test (creates if not exists)',
            default='test@example.com'
        )
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='Create test email data'
        )
        parser.add_argument(
            '--test-batch',
            action='store_true',
            help='Test batch categorization'
        )
        parser.add_argument(
            '--test-sync',
            action='store_true',
            help='Test cross-account sync'
        )
        parser.add_argument(
            '--show-stats',
            action='store_true',
            help='Show categorization statistics'
        )
    
    def handle(self, *args, **options):
        user_email = options['user_email']
        
        # Get or create test user
        user, created = User.objects.get_or_create(
            email=user_email,
            defaults={
                'username': user_email.split('@')[0],
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created test user: {user_email}')
            )
        else:
            self.stdout.write(f'Using existing user: {user_email}')
        
        # Create test data if requested
        if options['create_test_data']:
            self.create_test_data(user)
        
        # Test individual categorization
        self.test_individual_categorization(user)
        
        # Test batch categorization if requested
        if options['test_batch']:
            self.test_batch_categorization(user)
        
        # Test cross-account sync if requested
        if options['test_sync']:
            self.test_cross_account_sync(user)
        
        # Show statistics if requested
        if options['show_stats']:
            self.show_statistics(user)
    
    def create_test_data(self, user):
        """Create test email accounts and messages"""
        self.stdout.write('Creating test data...')
        
        # Create test email accounts
        gmail_account, created = EmailAccount.objects.get_or_create(
            user=user,
            email='test@gmail.com',
            provider='gmail',
            defaults={
                'is_active': True,
                'access_token': 'test_gmail_token',
                'refresh_token': 'test_gmail_refresh'
            }
        )
        
        outlook_account, created = EmailAccount.objects.get_or_create(
            user=user,
            email='test@outlook.com',
            provider='outlook',
            defaults={
                'is_active': True,
                'access_token': 'test_outlook_token',
                'refresh_token': 'test_outlook_refresh'
            }
        )
        
        # Test email data
        test_emails = [
            {
                'account': gmail_account,
                'subject': 'URGENT: Server downtime requires immediate action',
                'sender': 'alerts@company.com',
                'body': 'Critical server alert: Production servers are experiencing downtime. Immediate response required.',
                'expected_category': 'urgent'
            },
            {
                'account': outlook_account,
                'subject': 'Weekly team meeting notes and action items',
                'sender': 'team.lead@company.com',
                'body': 'Please review the weekly meeting notes and complete your assigned action items by Friday.',
                'expected_category': 'important'
            },
            {
                'account': gmail_account,
                'subject': 'Newsletter: Latest industry updates',
                'sender': 'newsletter@industry.com',
                'body': 'Stay updated with the latest news and trends in our industry. This week\'s highlights...',
                'expected_category': 'routine'
            },
            {
                'account': outlook_account,
                'subject': 'Special offer: 50% off all products this weekend!',
                'sender': 'sales@store.com',
                'body': 'Don\'t miss out on our biggest sale of the year. 50% off everything in store, limited time only!',
                'expected_category': 'promotional'
            },
            {
                'account': gmail_account,
                'subject': 'Congratulations! You\'ve won $1,000,000 in our lottery!',
                'sender': 'lottery.winner@scam.com',
                'body': 'You are the lucky winner of our international lottery! Send your bank details to claim your prize.',
                'expected_category': 'spam'
            }
        ]
        
        # Create test emails
        for email_data in test_emails:
            EmailMessage.objects.get_or_create(
                account=email_data['account'],
                message_id=f"test_{email_data['subject'][:20]}_{timezone.now().timestamp()}",
                defaults={
                    'subject': email_data['subject'],
                    'sender': email_data['sender'],
                    'recipient': email_data['account'].email,
                    'body_text': email_data['body'],
                    'category': 'pending',  # Will be categorized
                    'received_at': timezone.now()
                }
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created test data: 2 accounts, {len(test_emails)} emails')
        )
    
    def test_individual_categorization(self, user):
        """Test individual email categorization"""
        self.stdout.write('\n=== Testing Individual Email Categorization ===')
        
        engine = EmailCategorizationEngine(user)
        
        test_emails = [
            {
                'subject': 'URGENT: Security breach detected',
                'sender': 'security@company.com',
                'body': 'Immediate action required due to potential security breach.',
                'expected': 'urgent'
            },
            {
                'subject': 'Project update and next steps',
                'sender': 'project.manager@company.com',
                'body': 'Here\'s the latest project update with action items for the team.',
                'expected': 'important'
            },
            {
                'subject': 'Invoice #12345 - Payment due',
                'sender': 'billing@vendor.com',
                'body': 'Your monthly invoice is attached. Payment is due within 30 days.',
                'expected': 'routine'
            },
            {
                'subject': 'Flash Sale: Limited time offer!',
                'sender': 'marketing@retailer.com',
                'body': 'Don\'t miss our flash sale! 40% off selected items for 24 hours only.',
                'expected': 'promotional'
            },
            {
                'subject': 'You\'ve inherited millions! Act now!',
                'sender': 'prince@fakecountry.com',
                'body': 'I am a prince and I want to share my millions with you. Send your bank details.',
                'expected': 'spam'
            }
        ]
        
        correct_predictions = 0
        total_predictions = len(test_emails)
        
        for email_data in test_emails:
            result = engine.categorize_email(email_data)
            
            predicted = result['category']
            expected = email_data['expected']
            confidence = result['confidence']
            is_correct = predicted == expected
            
            if is_correct:
                correct_predictions += 1
            
            status_icon = '✅' if is_correct else '❌'
            
            self.stdout.write(
                f"{status_icon} Subject: {email_data['subject'][:50]}..."
            )
            self.stdout.write(
                f"    Expected: {expected} | Predicted: {predicted} | Confidence: {confidence:.2f}"
            )
            self.stdout.write(
                f"    Explanation: {result['explanation'][:100]}..."
            )
            self.stdout.write('')
        
        accuracy = (correct_predictions / total_predictions) * 100
        self.stdout.write(
            self.style.SUCCESS(
                f'Accuracy: {correct_predictions}/{total_predictions} ({accuracy:.1f}%)'
            )
        )
    
    def test_batch_categorization(self, user):
        """Test batch email categorization"""
        self.stdout.write('\n=== Testing Batch Email Categorization ===')
        
        batch_emails = [
            {'id': 'batch_1', 'subject': 'Meeting reminder for tomorrow', 'sender': 'calendar@company.com'},
            {'id': 'batch_2', 'subject': 'Your order has been shipped', 'sender': 'shipping@store.com'},
            {'id': 'batch_3', 'subject': 'CRITICAL: Database backup failed', 'sender': 'monitoring@company.com'},
            {'id': 'batch_4', 'subject': 'Win big with our casino games!', 'sender': 'casino@gambling.com'},
            {'id': 'batch_5', 'subject': 'Team lunch next Friday', 'sender': 'team@company.com'}
        ]
        
        results = categorize_emails_batch(batch_emails, user)
        
        for result in results:
            email_id = result['email_id']
            category = result['category']
            confidence = result['confidence']
            
            # Find original email
            original = next(e for e in batch_emails if e['id'] == email_id)
            
            self.stdout.write(
                f"📧 {original['subject'][:40]}... → {category} ({confidence:.2f})"
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Batch processed: {len(results)} emails')
        )
    
    def test_cross_account_sync(self, user):
        """Test cross-account synchronization"""
        self.stdout.write('\n=== Testing Cross-Account Synchronization ===')
        
        sync_manager = CrossAccountSyncManager(user)
        
        # Get sync status
        status = sync_manager.get_sync_status()
        self.stdout.write(f"Active accounts: {status['active_accounts']}")
        self.stdout.write(f"Total accounts: {status['total_accounts']}")
        
        # Test sync
        result = sync_manager.sync_all_accounts(force_full_sync=True)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sync completed: {result['accounts_synced']}/{result['total_accounts']} accounts"
                )
            )
            self.stdout.write(f"Emails processed: {result['total_emails_processed']}")
        else:
            self.stdout.write(
                self.style.ERROR(f"Sync failed: {result.get('message', 'Unknown error')}")
            )
    
    def show_statistics(self, user):
        """Show categorization statistics"""
        self.stdout.write('\n=== Categorization Statistics ===')
        
        engine = EmailCategorizationEngine(user)
        stats = engine.get_category_stats()
        
        self.stdout.write(f"Total emails (last 30 days): {stats['total_emails']}")
        self.stdout.write('')
        
        if stats['category_counts']:
            for category, count in stats['category_counts'].items():
                percentage = stats['category_percentages'].get(category, 0)
                self.stdout.write(f"  {category.capitalize():12} {count:4} emails ({percentage:5.1f}%)")
        else:
            self.stdout.write("No emails found for statistics")
        
        # Show account information
        accounts = EmailAccount.objects.filter(user=user)
        self.stdout.write(f"\nEmail accounts: {accounts.count()}")
        for account in accounts:
            email_count = EmailMessage.objects.filter(account=account).count()
            status = "Active" if account.is_active else "Inactive"
            self.stdout.write(f"  {account.email} ({account.provider}) - {email_count} emails [{status}]")
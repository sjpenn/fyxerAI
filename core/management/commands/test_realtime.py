"""
Django management command to test real-time email sync and notification features
"""

import time
import asyncio
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from core.services.notification_service import notification_service
from core.models import EmailAccount, EmailMessage

User = get_user_model()


class Command(BaseCommand):
    help = 'Test real-time email sync and notification features'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of the user to test notifications for',
            default='test@example.com'
        )
        parser.add_argument(
            '--test-notifications',
            action='store_true',
            help='Test WebSocket notifications'
        )
        parser.add_argument(
            '--test-sync-progress',
            action='store_true',
            help='Test sync progress notifications'
        )
        parser.add_argument(
            '--simulate-emails',
            action='store_true',
            help='Simulate new email arrivals'
        )
        parser.add_argument(
            '--test-urgent-alerts',
            action='store_true',
            help='Test urgent email alerts'
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
        
        # Test WebSocket connections
        self.test_websocket_connections()
        
        # Test basic notifications
        if options['test_notifications']:
            self.test_basic_notifications(user)
        
        # Test sync progress
        if options['test_sync_progress']:
            self.test_sync_progress_notifications(user)
        
        # Simulate email arrivals
        if options['simulate_emails']:
            self.simulate_email_arrivals(user)
        
        # Test urgent alerts
        if options['test_urgent_alerts']:
            self.test_urgent_alerts(user)
    
    def test_websocket_connections(self):
        """Test WebSocket channel layer connectivity"""
        self.stdout.write('\n=== Testing WebSocket Connections ===')
        
        channel_layer = get_channel_layer()
        
        if channel_layer is None:
            self.stdout.write(
                self.style.ERROR('❌ Channel layer not configured')
            )
            return False
        
        # Test channel layer connectivity
        try:
            test_channel = "test_channel"
            test_message = {"type": "test.message", "text": "Hello World"}
            
            # Send a test message
            async_to_sync(channel_layer.send)(test_channel, test_message)
            
            self.stdout.write(
                self.style.SUCCESS('✅ Channel layer working correctly')
            )
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Channel layer error: {e}')
            )
            return False
    
    def test_basic_notifications(self, user):
        """Test basic notification sending"""
        self.stdout.write('\n=== Testing Basic Notifications ===')
        
        try:
            # Test account connection notification
            account, created = EmailAccount.objects.get_or_create(
                user=user,
                email='test.notifications@gmail.com',
                provider='gmail',
                defaults={
                    'is_active': True,
                    'access_token': 'test_token',
                    'refresh_token': 'test_refresh'
                }
            )
            
            notification_service.notify_account_connected(account)
            self.stdout.write('✅ Account connection notification sent')
            
            # Test error notification
            notification_service.notify_account_error(
                user.id, 
                'test.error@outlook.com', 
                'Test error message'
            )
            self.stdout.write('✅ Account error notification sent')
            
            time.sleep(1)  # Brief pause between notifications
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Notification error: {e}')
            )
    
    def test_sync_progress_notifications(self, user):
        """Test sync progress notifications"""
        self.stdout.write('\n=== Testing Sync Progress Notifications ===')
        
        try:
            # Simulate sync starting
            notification_service.notify_sync_progress(user.id, {
                'status': 'starting',
                'total_accounts': 2,
                'completed_accounts': 0,
                'current_account': None
            })
            self.stdout.write('✅ Sync start notification sent')
            time.sleep(1)
            
            # Simulate account syncing
            notification_service.notify_sync_progress(user.id, {
                'status': 'syncing_account',
                'total_accounts': 2,
                'completed_accounts': 0,
                'current_account': 'test@gmail.com'
            })
            self.stdout.write('✅ Account syncing notification sent')
            time.sleep(1)
            
            # Simulate account completion
            notification_service.notify_sync_progress(user.id, {
                'status': 'account_completed',
                'total_accounts': 2,
                'completed_accounts': 1,
                'account_email': 'test@gmail.com',
                'emails_processed': 15
            })
            self.stdout.write('✅ Account completion notification sent')
            time.sleep(1)
            
            # Simulate sync completion
            notification_service.notify_sync_completed(user.id, {
                'success': True,
                'accounts_synced': 2,
                'total_accounts': 2,
                'total_emails_processed': 28,
                'sync_timestamp': timezone.now().isoformat()
            })
            self.stdout.write('✅ Sync completion notification sent')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Sync progress error: {e}')
            )
    
    def simulate_email_arrivals(self, user):
        """Simulate new email arrivals with notifications"""
        self.stdout.write('\n=== Simulating Email Arrivals ===')
        
        try:
            # Get or create test account
            account, _ = EmailAccount.objects.get_or_create(
                user=user,
                email='test@gmail.com',
                provider='gmail',
                defaults={
                    'is_active': True,
                    'access_token': 'test_token',
                    'refresh_token': 'test_refresh'
                }
            )
            
            # Simulate different types of emails
            test_emails = [
                {
                    'subject': 'Project Update - Please Review',
                    'sender': 'manager@company.com',
                    'body': 'Please review the latest project updates and provide feedback.',
                    'category': 'important'
                },
                {
                    'subject': 'Weekly Newsletter - Tech News',
                    'sender': 'newsletter@techsite.com',
                    'body': 'Your weekly digest of technology news and updates.',
                    'category': 'routine'
                },
                {
                    'subject': 'Special Offer - 50% Off Everything!',
                    'sender': 'sales@retailstore.com',
                    'body': 'Limited time offer - save 50% on all products.',
                    'category': 'promotional'
                }
            ]
            
            for i, email_data in enumerate(test_emails):
                # Create email in database
                email = EmailMessage.objects.create(
                    account=account,
                    message_id=f'test_email_{i}_{timezone.now().timestamp()}',
                    subject=email_data['subject'],
                    sender=email_data['sender'],
                    recipient=account.email,
                    body_text=email_data['body'],
                    category=email_data['category'],
                    received_at=timezone.now(),
                    is_read=False
                )
                
                # Send notification
                notification_service.notify_new_email(email)
                
                self.stdout.write(f'✅ Simulated email: {email_data["subject"][:40]}...')
                time.sleep(2)  # Space out the arrivals
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Email simulation error: {e}')
            )
    
    def test_urgent_alerts(self, user):
        """Test urgent email alerts"""
        self.stdout.write('\n=== Testing Urgent Email Alerts ===')
        
        try:
            # Get or create test account
            account, _ = EmailAccount.objects.get_or_create(
                user=user,
                email='test@gmail.com',
                provider='gmail',
                defaults={
                    'is_active': True,
                    'access_token': 'test_token',
                    'refresh_token': 'test_refresh'
                }
            )
            
            # Create urgent email
            urgent_email = EmailMessage.objects.create(
                account=account,
                message_id=f'urgent_test_{timezone.now().timestamp()}',
                subject='URGENT: Server outage requires immediate attention',
                sender='alerts@company.com',
                recipient=account.email,
                body_text='Critical server outage detected. Immediate response required.',
                category='urgent',
                priority=5,
                received_at=timezone.now(),
                is_read=False
            )
            
            # Send urgent notification
            notification_service.notify_urgent_email(urgent_email)
            
            self.stdout.write('✅ Urgent email alert sent')
            self.stdout.write(f'   Subject: {urgent_email.subject}')
            self.stdout.write(f'   Sender: {urgent_email.sender}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Urgent alert error: {e}')
            )
    
    def get_websocket_status(self):
        """Check WebSocket server status"""
        self.stdout.write('\n=== WebSocket Status ===')
        
        channel_layer = get_channel_layer()
        
        if channel_layer:
            self.stdout.write(f'Channel layer backend: {channel_layer.__class__.__name__}')
            
            # Try to get Redis connection info if using Redis
            if hasattr(channel_layer, 'hosts'):
                self.stdout.write(f'Redis hosts: {channel_layer.hosts}')
        else:
            self.stdout.write('No channel layer configured')
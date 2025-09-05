"""
Django management command to populate test data for development
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime
import random

from core.models import EmailAccount, EmailMessage, UserPreference, Meeting

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with test data for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before creating new data'
        )
        parser.add_argument(
            '--users',
            type=int,
            default=2,
            help='Number of test users to create'
        )
        parser.add_argument(
            '--emails-per-account',
            type=int,
            default=25,
            help='Number of emails per account'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing test data...')
            User.objects.filter(username__startswith='testuser').delete()
            
        self.create_test_users(options['users'])
        self.create_test_emails(options['emails_per_account'])
        self.create_test_meetings()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated test data')
        )

    def create_test_users(self, count):
        self.stdout.write(f'Creating {count} test users...')
        
        for i in range(count):
            username = f'testuser{i+1}'
            email = f'testuser{i+1}@example.com'
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': f'Test',
                    'last_name': f'User {i+1}',
                    'is_active': True,
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'  Created user: {username}')
                
                # Create user preferences
                UserPreference.objects.get_or_create(
                    user=user,
                    defaults={
                        'default_tone': random.choice(['professional', 'friendly', 'casual']),
                        'auto_categorize': True,
                        'auto_generate_drafts': True,
                        'ai_confidence_threshold': 0.7
                    }
                )
                
                # Create email accounts
                self.create_email_accounts(user)
            else:
                self.stdout.write(f'  User {username} already exists')

    def create_email_accounts(self, user):
        """Create test email accounts for the user"""
        accounts_data = [
            {
                'provider': 'gmail',
                'email_address': f'{user.username}@gmail.com',
                'display_name': f'{user.first_name} {user.last_name}',
            },
            {
                'provider': 'outlook',
                'email_address': f'{user.username}@outlook.com',
                'display_name': f'{user.first_name} {user.last_name}',
            }
        ]
        
        for account_data in accounts_data:
            account, created = EmailAccount.objects.get_or_create(
                user=user,
                email_address=account_data['email_address'],
                defaults={
                    'provider': account_data['provider'],
                    'display_name': account_data['display_name'],
                    'access_token': 'dummy_access_token',
                    'refresh_token': 'dummy_refresh_token',
                    'token_expires_at': timezone.now() + timedelta(hours=1),
                    'is_active': True,
                    'sync_enabled': True,
                    'last_sync': timezone.now() - timedelta(minutes=random.randint(1, 60))
                }
            )
            
            if created:
                self.stdout.write(f'    Created account: {account_data["email_address"]}')

    def create_test_emails(self, emails_per_account):
        """Create test emails for all accounts"""
        self.stdout.write(f'Creating {emails_per_account} emails per account...')
        
        # Sample email data
        subjects = [
            "Project Update Required",
            "Meeting Reminder: Q4 Planning",
            "Invoice #12345 - Payment Due",
            "Welcome to Our Newsletter!",
            "Your Order Has Been Shipped",
            "Security Alert: New Login Detected",
            "Team Lunch This Friday",
            "Quarterly Report - Review Needed",
            "Special Offer: 50% Off Everything!",
            "Password Reset Request",
            "Meeting Notes from Yesterday",
            "Action Required: Update Your Profile",
            "Weekly Status Report",
            "New Features Available",
            "System Maintenance Scheduled",
        ]
        
        senders = [
            ('alice@company.com', 'Alice Smith'),
            ('bob.jones@partner.com', 'Bob Jones'),
            ('notifications@service.com', 'Service Notifications'),
            ('marketing@shop.com', 'Marketing Team'),
            ('support@platform.com', 'Customer Support'),
            ('hr@company.com', 'HR Department'),
            ('admin@system.com', 'System Admin'),
            ('newsletter@blog.com', 'Tech Blog'),
            ('sales@vendor.com', 'Sales Team'),
            ('security@service.com', 'Security Team'),
        ]
        
        categories = [
            ('urgent', 'high'),
            ('important', 'high'),
            ('important', 'medium'),
            ('newsletter', 'low'),
            ('promotion', 'low'),
            ('social', 'low'),
            ('notification', 'medium'),
            ('other', 'medium'),
        ]
        
        for account in EmailAccount.objects.all():
            for i in range(emails_per_account):
                sender_email, sender_name = random.choice(senders)
                subject = random.choice(subjects)
                category, priority = random.choice(categories)
                
                # Generate realistic received time (last 30 days)
                days_ago = random.randint(0, 30)
                hours_ago = random.randint(0, 23)
                minutes_ago = random.randint(0, 59)
                
                received_at = timezone.now() - timedelta(
                    days=days_ago, hours=hours_ago, minutes=minutes_ago
                )
                
                EmailMessage.objects.get_or_create(
                    account=account,
                    message_id=f'{account.provider}-{i+1}-{random.randint(1000, 9999)}',
                    defaults={
                        'subject': subject,
                        'sender_email': sender_email,
                        'sender_name': sender_name,
                        'recipient_emails': [account.email_address],
                        'cc_emails': [],
                        'bcc_emails': [],
                        'body_text': self.generate_email_body(subject, sender_name),
                        'body_html': '',
                        'category': category,
                        'priority': priority,
                        'ai_confidence': random.uniform(0.6, 0.95),
                        'manual_override': random.choice([True, False]),
                        'is_read': random.choice([True, False]),
                        'is_starred': random.choice([True, False, False, False]),  # 25% chance
                        'has_attachments': random.choice([True, False, False]),    # 33% chance
                        'has_draft_reply': random.choice([True, False, False, False]),  # 25% chance
                        'received_at': received_at,
                    }
                )

        self.stdout.write('  Test emails created successfully')

    def generate_email_body(self, subject, sender_name):
        """Generate a realistic email body based on subject and sender"""
        templates = [
            f"Hi there,\n\nI hope this email finds you well. Regarding {subject.lower()}, I wanted to reach out and discuss the next steps.\n\nPlease let me know your thoughts.\n\nBest regards,\n{sender_name}",
            f"Hello,\n\nThis is a quick update about {subject.lower()}. Everything is progressing as planned and we should have more details soon.\n\nThanks,\n{sender_name}",
            f"Dear Team,\n\nI'm writing to inform you about {subject.lower()}. Please review the attached information and get back to me with any questions.\n\nKind regards,\n{sender_name}",
            f"Hi,\n\nJust a friendly reminder about {subject.lower()}. Don't forget to mark your calendar!\n\nCheers,\n{sender_name}",
        ]
        
        return random.choice(templates)

    def create_test_meetings(self):
        """Create test meetings for users"""
        self.stdout.write('Creating test meetings...')
        
        meeting_titles = [
            "Weekly Team Standup",
            "Q4 Planning Session",
            "Client Presentation",
            "Product Demo",
            "All Hands Meeting",
            "1:1 with Manager",
            "Architecture Review",
            "Sprint Retrospective",
        ]
        
        platforms = ['zoom', 'teams', 'meet']
        
        for user in User.objects.filter(username__startswith='testuser'):
            for i in range(3):  # 3 meetings per user
                title = random.choice(meeting_titles)
                platform = random.choice(platforms)
                
                # Schedule meetings in the past week and next week
                if i == 0:
                    # Past meeting
                    start_time = timezone.now() - timedelta(days=random.randint(1, 7))
                    status = 'completed'
                    has_recording = True
                    has_transcript = True
                elif i == 1:
                    # Today or tomorrow
                    start_time = timezone.now() + timedelta(hours=random.randint(1, 48))
                    status = 'scheduled'
                    has_recording = False
                    has_transcript = False
                else:
                    # Future meeting
                    start_time = timezone.now() + timedelta(days=random.randint(2, 14))
                    status = 'scheduled'
                    has_recording = False
                    has_transcript = False
                
                end_time = start_time + timedelta(minutes=60)  # 1 hour meetings
                
                Meeting.objects.get_or_create(
                    user=user,
                    title=title,
                    scheduled_start=start_time,
                    defaults={
                        'description': f'Regular {title.lower()} meeting',
                        'platform': platform,
                        'meeting_url': f'https://{platform}.example.com/j/{random.randint(100000, 999999)}',
                        'scheduled_end': end_time,
                        'organizer_email': user.email,
                        'participants': [
                            'participant1@example.com',
                            'participant2@example.com'
                        ],
                        'status': status,
                        'has_recording': has_recording,
                        'has_transcript': has_transcript,
                        'summary': 'Meeting summary will be generated here' if status == 'completed' else '',
                        'action_items': ['Review quarterly goals', 'Update project timeline'] if status == 'completed' else [],
                        'key_topics': ['Project updates', 'Budget review'] if status == 'completed' else [],
                    }
                )
        
        self.stdout.write('  Test meetings created successfully')
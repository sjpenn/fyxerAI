"""
Django management command to setup Gmail labels for email triage
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.services.gmail_service import get_gmail_service


class Command(BaseCommand):
    help = 'Setup FYXERAI Gmail labels for email categorization'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Gmail email address to setup labels for'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing labels'
        )
    
    def handle(self, *args, **options):
        email = options['email']
        force = options['force']
        
        self.stdout.write(f'Setting up FYXERAI labels for {email}...')
        
        try:
            # Initialize Gmail service
            gmail_service = get_gmail_service(email)
            
            if not gmail_service.is_authenticated():
                self.stdout.write(
                    self.style.ERROR(
                        f'Gmail service not authenticated for {email}. '
                        'Please complete OAuth flow first.'
                    )
                )
                return
            
            # Setup labels
            label_ids = gmail_service.setup_fyxerai_labels()
            
            self.stdout.write(self.style.SUCCESS('Successfully created labels:'))
            for category, label_id in label_ids.items():
                label_name = gmail_service.FYXERAI_LABELS[category]['name']
                self.stdout.write(f'  - {label_name} (ID: {label_id})')
            
            # Test service status
            status = gmail_service.get_service_status()
            self.stdout.write(f'\nService Status:')
            self.stdout.write(f'  - Authenticated: {status["authenticated"]}')
            self.stdout.write(f'  - Email: {status["email_address"]}')
            self.stdout.write(f'  - Total Messages: {status["messages_total"]}')
            
        except Exception as e:
            raise CommandError(f'Failed to setup Gmail labels: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Gmail labels setup completed for {email}'
            )
        )
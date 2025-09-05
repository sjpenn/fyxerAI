"""
Django management command to test email triage functionality
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.services.gmail_service import get_gmail_service
from core.services.openai_service import get_openai_service
from core.services.label_manager import process_email_triage
import json


class Command(BaseCommand):
    help = 'Test email triage functionality with real Gmail data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Gmail email address to test with'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for emails (default: 7)'
        )
        parser.add_argument(
            '--max-emails',
            type=int,
            default=10,
            help='Maximum number of emails to process (default: 10)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test categorization without applying labels'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed processing information'
        )
    
    def handle(self, *args, **options):
        email = options['email']
        days = options['days']
        max_emails = options['max_emails']
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(f'Testing email triage for {email}...')
        self.stdout.write(f'Looking back {days} days, processing up to {max_emails} emails')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No labels will be applied'))
        
        try:
            # Test Gmail service
            self.stdout.write('1. Testing Gmail service...')
            # Use read-only scope for listing and status
            gmail_service = get_gmail_service(
                email,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
            
            if not gmail_service.is_authenticated():
                self.stdout.write(
                    self.style.ERROR(
                        f'Gmail service not authenticated for {email}. '
                        'Please complete OAuth flow first.'
                    )
                )
                return
            
            status = gmail_service.get_service_status()
            self.stdout.write(self.style.SUCCESS(f'   ✓ Gmail authenticated ({status["email_address"]})'))
            
            # Test OpenAI service
            self.stdout.write('2. Testing OpenAI service...')
            openai_service = get_openai_service()
            
            if openai_service.is_available():
                ai_status = openai_service.get_service_status()
                self.stdout.write(self.style.SUCCESS(f'   ✓ OpenAI available (model: {ai_status["model"]})'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠ OpenAI not available, using fallback'))
            
            # Fetch emails
            self.stdout.write('3. Fetching emails...')
            emails = gmail_service.fetch_emails(max_results=max_emails)
            
            if not emails:
                self.stdout.write(self.style.WARNING('   No emails found to process'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'   ✓ Found {len(emails)} emails'))
            
            if verbose:
                for i, email in enumerate(emails[:5]):  # Show first 5
                    self.stdout.write(f'     {i+1}. {email["subject"][:50]}... from {email["sender"]}')
                if len(emails) > 5:
                    self.stdout.write(f'     ... and {len(emails) - 5} more emails')
            
            # Test categorization
            self.stdout.write('4. Testing categorization...')
            
            if dry_run:
                # Just test categorization without label application
                categorization_results = openai_service.categorize_emails_batch(emails[:5])
                
                self.stdout.write(self.style.SUCCESS('   ✓ Categorization test completed'))
                
                for result in categorization_results:
                    email_id = result['email_id']
                    category = result['category']
                    confidence = result['confidence']
                    ai_powered = result.get('ai_powered', False)
                    
                    # Find corresponding email
                    email = next((e for e in emails if e['id'] == email_id), None)
                    subject = email['subject'][:40] if email else 'Unknown'
                    
                    ai_indicator = '🤖' if ai_powered else '📋'
                    self.stdout.write(
                        f'     {ai_indicator} {subject}... → {category.upper()} ({confidence:.2f})'
                    )
                
            else:
                # Full triage with label application
                triage_results = process_email_triage(email, emails[:max_emails], 'gmail')
                
                if triage_results['success']:
                    self.stdout.write(self.style.SUCCESS('   ✓ Full triage completed'))
                    
                    stats = triage_results['statistics']
                    self.stdout.write('   Results:')
                    for category, count in stats.items():
                        if count > 0:
                            self.stdout.write(f'     - {category.title()}: {count} emails')
                    
                    if triage_results.get('errors'):
                        self.stdout.write(self.style.WARNING(f'   ⚠ {len(triage_results["errors"])} errors occurred'))
                        if verbose:
                            for error in triage_results['errors'][:3]:
                                self.stdout.write(f'     - {error}')
                else:
                    self.stdout.write(self.style.ERROR(f'   ✗ Triage failed: {triage_results.get("error")}'))
            
            # Summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('TRIAGE TEST COMPLETED'))
            self.stdout.write(f'Processed: {len(emails)} emails')
            self.stdout.write(f'Platform: Gmail')
            self.stdout.write(f'AI Service: {"Available" if openai_service.is_available() else "Fallback"}')
            
        except Exception as e:
            raise CommandError(f'Triage test failed: {e}')

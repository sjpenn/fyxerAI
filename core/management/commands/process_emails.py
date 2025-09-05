"""
Django management command for processing emails with the unified service
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from core.services.unified_email_service import (
    UnifiedEmailService,
    GmailIntegration,
    OutlookIntegration
)
import json


class Command(BaseCommand):
    help = 'Process emails from Gmail and Outlook with AI classification and summarization'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--gmail',
            type=str,
            help='Gmail address to process'
        )
        parser.add_argument(
            '--outlook',
            type=str,
            help='Outlook/Microsoft 365 email to process'
        )
        parser.add_argument(
            '--auth-gmail',
            action='store_true',
            help='Run Gmail OAuth authorization flow'
        )
        parser.add_argument(
            '--auth-outlook',
            action='store_true',
            help='Run Outlook device auth flow'
        )
        parser.add_argument(
            '--classify',
            action='store_true',
            help='Run classification on stored emails'
        )
        parser.add_argument(
            '--summarize',
            action='store_true',
            help='Generate summaries for emails'
        )
        parser.add_argument(
            '--apply-labels',
            action='store_true',
            help='Apply categories back to email sources'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show email processing statistics'
        )
        parser.add_argument(
            '--query',
            type=str,
            default='newer_than:7d',
            help='Gmail query (default: newer_than:7d)'
        )
    
    def handle(self, *args, **options):
        service = UnifiedEmailService()
        
        # Handle authentication flows
        if options['auth_gmail'] and options['gmail']:
            self.stdout.write(self.style.WARNING('Starting Gmail OAuth flow...'))
            gmail = GmailIntegration(options['gmail'])
            flow = gmail.get_oauth_flow()
            
            # For command line, use local server flow
            creds = flow.run_local_server(port=0)
            gmail.credentials = creds
            gmail._save_credentials()
            
            self.stdout.write(self.style.SUCCESS('Gmail authentication successful!'))
        
        if options['auth_outlook'] and options['outlook']:
            self.stdout.write(self.style.WARNING('Starting Outlook device auth flow...'))
            outlook = OutlookIntegration(options['outlook'])
            flow = outlook.get_device_flow()
            
            self.stdout.write(self.style.NOTICE(flow['message']))
            
            if outlook.acquire_token_by_device_flow(flow):
                self.stdout.write(self.style.SUCCESS('Outlook authentication successful!'))
            else:
                self.stdout.write(self.style.ERROR('Outlook authentication failed'))
        
        # Ingest emails
        if options['gmail']:
            self.stdout.write(f"Ingesting Gmail messages for {options['gmail']}...")
            count = service.ingest_gmail(options['gmail'], query=options['query'])
            self.stdout.write(self.style.SUCCESS(f"Ingested {count} Gmail messages"))
        
        if options['outlook']:
            self.stdout.write(f"Ingesting Outlook messages for {options['outlook']}...")
            count = service.ingest_outlook(options['outlook'])
            self.stdout.write(self.style.SUCCESS(f"Ingested {count} Outlook messages"))
        
        # Process emails
        if options['classify']:
            self.stdout.write("Classifying emails...")
            count = service.classify_emails()
            self.stdout.write(self.style.SUCCESS(f"Classified {count} emails"))
        
        if options['summarize']:
            self.stdout.write("Generating email summaries...")
            count = service.summarize_emails()
            self.stdout.write(self.style.SUCCESS(f"Summarized {count} emails"))
        
        if options['apply_labels']:
            self.stdout.write("Applying labels to email sources...")
            # This would need to iterate through emails and apply labels
            # For now, just show a message
            self.stdout.write(self.style.WARNING("Label application requires email IDs"))
        
        # Show statistics
        if options['stats']:
            stats = service.get_email_stats()
            
            self.stdout.write("\n" + self.style.HTTP_INFO("=== Email Processing Statistics ==="))
            self.stdout.write(f"Total emails: {stats['total']}")
            
            if stats['by_source']:
                self.stdout.write("\nBy source:")
                for source, count in stats['by_source'].items():
                    self.stdout.write(f"  {source}: {count}")
            
            self.stdout.write(f"\nClassified: {stats['classified']}")
            self.stdout.write(f"Summarized: {stats['summarized']}")
            
            if stats['categories']:
                self.stdout.write("\nTop categories:")
                sorted_cats = sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True)[:5]
                for cat, count in sorted_cats:
                    self.stdout.write(f"  {cat}: {count}")
        
        # Example: Generate a draft reply (would need email ID)
        if not any([options[k] for k in ['gmail', 'outlook', 'classify', 'summarize', 'stats']]):
            self.stdout.write(self.style.NOTICE(
                "\nUsage examples:\n"
                "  # Authenticate Gmail\n"
                "  python manage.py process_emails --auth-gmail --gmail user@gmail.com\n\n"
                "  # Ingest and process Gmail\n"
                "  python manage.py process_emails --gmail user@gmail.com --classify --summarize\n\n"
                "  # Authenticate Outlook\n"
                "  python manage.py process_emails --auth-outlook --outlook user@outlook.com\n\n"
                "  # Process all stored emails\n"
                "  python manage.py process_emails --classify --summarize --stats\n"
            ))
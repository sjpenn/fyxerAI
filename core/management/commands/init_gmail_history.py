from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import EmailAccount
from core.services.gmail_service import get_gmail_service


class Command(BaseCommand):
    help = 'Initialize gmail_history_id for Gmail accounts and optionally backfill recent emails'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Specific Gmail address to init')
        parser.add_argument('--user', type=str, help='Username to filter accounts')
        parser.add_argument('--backfill-days', type=int, default=0, help='Backfill N days (0 = none)')

    def handle(self, *args, **opts):
        qs = EmailAccount.objects.filter(provider='gmail', is_active=True)
        if opts.get('email'):
            qs = qs.filter(email_address=opts['email'])
        if opts.get('user'):
            User = get_user_model()
            try:
                u = User.objects.get(username=opts['user'])
                qs = qs.filter(user=u)
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR('User not found'))
                return

        if not qs.exists():
            self.stdout.write(self.style.WARNING('No Gmail accounts found'))
            return

        for acct in qs:
            self.stdout.write(f'Initializing {acct.email_address}...')
            svc = get_gmail_service(acct.email_address, scopes=['https://www.googleapis.com/auth/gmail.readonly'])
            if not svc or not svc.is_authenticated():
                self.stderr.write(self.style.ERROR('  Not authenticated'))
                continue
            status = svc.get_service_status()
            hid = status.get('history_id')
            if hid:
                acct.gmail_history_id = str(hid)
                acct.save(update_fields=['gmail_history_id', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'  historyId set to {hid}'))
            else:
                self.stderr.write(self.style.WARNING('  historyId unavailable'))

            # Optional backfill: triggers a single fetch_emails to seed local DB consumers if needed
            days = int(opts.get('backfill_days') or 0)
            if days > 0:
                from django.utils import timezone
                from datetime import timedelta
                svc.fetch_emails(since_date=timezone.now()-timedelta(days=days), max_results=100)
                self.stdout.write(self.style.SUCCESS(f'  Backfill fetch initiated for last {days} days'))


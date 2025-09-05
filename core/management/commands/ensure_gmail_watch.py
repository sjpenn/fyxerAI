from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import EmailAccount
from core.services.gmail_service import get_gmail_service
from django.conf import settings


class Command(BaseCommand):
    help = 'Ensure Gmail watch is active for all Gmail accounts, renew if expiring soon.'

    def add_arguments(self, parser):
        parser.add_argument('--renew-within-mins', type=int, default=1440, help='Renew if expiring within N minutes (default 1440 = 24h)')

    def handle(self, *args, **opts):
        topic = getattr(settings, 'GMAIL_PUBSUB_TOPIC', '')
        if not topic:
            self.stderr.write(self.style.ERROR('GMAIL_PUBSUB_TOPIC not configured in settings'))
            return
        threshold = timezone.now() + timezone.timedelta(minutes=opts['renew_within_mins'])
        qs = EmailAccount.objects.filter(provider='gmail', is_active=True)
        if not qs.exists():
            self.stdout.write('No Gmail accounts found')
            return
        for acct in qs:
            svc = get_gmail_service(acct.email_address, scopes=['https://www.googleapis.com/auth/gmail.readonly'])
            if not svc or not svc.is_authenticated():
                self.stderr.write(self.style.WARNING(f'Skipping {acct.email_address}: not authenticated'))
                continue
            needs_watch = not acct.gmail_watch_expiration or acct.gmail_watch_expiration <= threshold
            if needs_watch:
                self.stdout.write(f'Starting/renewing watch for {acct.email_address}...')
                resp = svc.start_watch(topic, label_ids=getattr(settings, 'GMAIL_PUBSUB_LABELS', ['INBOX']))
                if resp:
                    self.stdout.write(self.style.SUCCESS(f'Watch set: historyId={resp.get("historyId")}'))
                else:
                    self.stderr.write(self.style.ERROR('Failed to set watch'))
            else:
                self.stdout.write(f'Watch active for {acct.email_address} until {acct.gmail_watch_expiration}')


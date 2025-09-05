import json
import sys
import time
from typing import List

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

try:
    import msal  # type: ignore
except Exception as e:  # pragma: no cover
    msal = None


class Command(BaseCommand):
    help = (
        "Verify Microsoft Graph connectivity with device code flow using a Client ID.\n"
        "Prompts you to sign in and then fetches /me and 1 inbox message."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-id",
            dest="client_id",
            help="Azure AD Application (Client) ID. Defaults to MICROSOFT_CLIENT_ID from settings.",
        )
        parser.add_argument(
            "--tenant",
            dest="tenant",
            default="common",
            help="Tenant ID or 'common' (default).",
        )
        parser.add_argument(
            "--scopes",
            dest="scopes",
            nargs="*",
            default=[
                "User.Read",
                "Mail.Read",
            ],
            help="Scopes to request (space separated). Defaults: User.Read Mail.Read",
        )

    def handle(self, *args, **options):
        if msal is None:
            raise CommandError(
                "The 'msal' package is required. Please run: pip install msal"
            )

        client_id = options.get("client_id") or getattr(settings, "MICROSOFT_CLIENT_ID", "")
        tenant = options.get("tenant") or "common"
        scopes: List[str] = options.get("scopes") or ["User.Read", "Mail.Read"]

        if not client_id or client_id.strip().lower() in {"your-microsoft-client-id", "", "changeme"}:
            raise CommandError(
                "MICROSOFT_CLIENT_ID is not set. Pass --client-id or set MICROSOFT_CLIENT_ID in .env."
            )

        authority = f"https://login.microsoftonline.com/{tenant}"
        self.stdout.write(self.style.NOTICE(f"Authority: {authority}"))
        self.stdout.write(self.style.NOTICE(f"Scopes: {' '.join(scopes)}"))

        app = msal.PublicClientApplication(client_id=client_id, authority=authority)

        # Try cached account first (if any future caching is added)
        # For now always initiate device code flow
        flow = app.initiate_device_flow(scopes=[f"https://graph.microsoft.com/{s}" if not s.startswith("http") else s for s in scopes])
        if "user_code" not in flow:
            raise CommandError("Failed to create device flow. Response: %s" % json.dumps(flow))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Complete sign-in to continue:"))
        self.stdout.write(flow["message"])  # includes verification URL + user code
        self.stdout.write("")

        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise CommandError(
                f"Failed to acquire token. Error: {result.get('error')}, Desc: {result.get('error_description')}"
            )

        token = result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Verify identity
        me_resp = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=20)
        if me_resp.status_code != 200:
            raise CommandError(f"/me request failed: {me_resp.status_code} {me_resp.text}")

        me = me_resp.json()
        display = me.get("displayName", "unknown")
        upn = me.get("userPrincipalName", me.get("mail", "unknown"))
        self.stdout.write(self.style.SUCCESS(f"Signed in as: {display} ({upn})"))

        # Try to fetch one inbox message to confirm Mail.Read
        msg_resp = requests.get(
            "https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages?$top=1",
            headers=headers,
            timeout=20,
        )
        if msg_resp.status_code == 200:
            data = msg_resp.json()
            count = len(data.get("value", []))
            if count:
                subj = data["value"][0].get("subject", "(no subject)")
                self.stdout.write(self.style.SUCCESS(f"Inbox reachable. Sample subject: {subj}"))
            else:
                self.stdout.write(self.style.WARNING("Inbox reachable but no messages returned."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Mail request not successful ({msg_resp.status_code}). Scope may be missing: {msg_resp.text}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Microsoft Graph connectivity verified."))


"""
FYXERAI Gmail API Service
Handles Gmail API integration for email retrieval and label management
"""

import os
import json
import base64
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

# Gmail API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    # Graceful fallback if Google API client not installed
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception

import logging

logger = logging.getLogger(__name__)

class GmailService:
    """
    Gmail API service for email operations and label management.
    Handles OAuth2 authentication and provides methods for email triage.
    """
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels',
        'https://www.googleapis.com/auth/gmail.send'
    ]
    
    # FYXERAI label configuration
    FYXERAI_LABELS = {
        'urgent': {
            'name': 'FYXERAI/Urgent',
            'color': {'textColor': '#ffffff', 'backgroundColor': '#d93025'},
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        },
        'important': {
            'name': 'FYXERAI/Important',
            'color': {'textColor': '#000000', 'backgroundColor': '#fbbc04'},
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        },
        'routine': {
            'name': 'FYXERAI/Routine',
            'color': {'textColor': '#ffffff', 'backgroundColor': '#34a853'},
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        },
        'promotional': {
            'name': 'FYXERAI/Promotional',
            'color': {'textColor': '#000000', 'backgroundColor': '#ff6d01'},
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        },
        'spam': {
            'name': 'FYXERAI/Spam',
            'color': {'textColor': '#ffffff', 'backgroundColor': '#9aa0a6'},
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        }
    }
    
    def __init__(self, user_email: str, scopes: Optional[List[str]] = None):
        self.user_email = user_email
        self.service = None
        self.credentials = None
        # Allow callers to minimize scopes for read-only operations
        self.scopes = scopes or self.SCOPES
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Gmail API service with proper authentication."""
        if not build:
            logger.warning("Google API client not installed. Gmail integration disabled.")
            return None
            
        try:
            # Load credentials from database or cache
            creds = self._load_credentials()
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing Gmail credentials")
                    creds.refresh(Request())
                    self._save_credentials(creds)
                else:
                    logger.warning("No valid Gmail credentials found. OAuth flow required.")
                    return None
            
            self.credentials = creds
            self.service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
            logger.info(f"Gmail service initialized for {self.user_email}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            self.service = None
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load OAuth2 credentials from cache or database."""
        # Check cache first
        cache_key = f"gmail_creds_{self.user_email}"
        cached_creds = cache.get(cache_key)
        
        if cached_creds:
            try:
                return Credentials.from_authorized_user_info(cached_creds)
            except Exception as e:
                logger.warning(f"Failed to load cached credentials: {e}")
        
        # Load from database EmailAccount model
        try:
            from ..models import EmailAccount
            account = EmailAccount.objects.filter(
                email_address=self.user_email,
                is_active=True
            ).order_by('-updated_at').first()
            if not account:
                return None

            token = account.decrypt_token(account.access_token)
            refresh_token = account.decrypt_token(account.refresh_token)

            creds = Credentials(
                token=token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=self.scopes,
            )
            # If expired or missing token, refresh will happen in initializer
            return creds
        except Exception as e:
            logger.error(f"Failed to load credentials from DB: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials):
        """Save OAuth2 credentials to cache and database."""
        if not creds:
            return
            
        # Save to cache (1 hour expiry)
        cache_key = f"gmail_creds_{self.user_email}"
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        cache.set(cache_key, creds_data, 3600)
        
        # Save to database EmailAccount model
        try:
            from ..models import EmailAccount
            account = EmailAccount.objects.filter(
                email_address=self.user_email,
                is_active=True
            ).order_by('-updated_at').first()
            if account:
                account.access_token = account.encrypt_token(creds.token)
                if creds.refresh_token:
                    account.refresh_token = account.encrypt_token(creds.refresh_token)
                # Use provided expiry if present; otherwise approximate 1 hour
                expires_at = getattr(creds, 'expiry', None)
                if expires_at:
                    # Ensure timezone-aware
                    if timezone.is_naive(expires_at):
                        from datetime import timezone as dt_tz
                        expires_at = expires_at.replace(tzinfo=dt_tz.utc)
                    account.token_expires_at = expires_at
                else:
                    account.token_expires_at = timezone.now() + timedelta(seconds=3600)
                account.save(update_fields=[
                    'access_token', 'refresh_token', 'token_expires_at', 'updated_at'
                ])
        except Exception as e:
            logger.warning(f"Failed to persist refreshed Gmail credentials: {e}")

        logger.info("Gmail credentials saved to cache and DB (if available)")
    
    def is_authenticated(self) -> bool:
        """Check if Gmail service is properly authenticated."""
        return self.service is not None and self.credentials is not None
    
    def get_oauth_url(self) -> str:
        """Generate OAuth2 authorization URL for Gmail access."""
        if not InstalledAppFlow:
            raise Exception("Google API client not installed")
            
        # Use client credentials from settings
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [f"{settings.BASE_URL}/auth/gmail/callback/"]
            }
        }
        
        flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
        flow.redirect_uri = f"{settings.BASE_URL}/auth/gmail/callback/"
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            login_hint=self.user_email
        )
        
        return auth_url
    
    def fetch_emails(self, since_date: datetime = None, max_results: int = 100, include_bodies: bool = True) -> List[Dict]:
        """
        Fetch emails from Gmail API with date filtering.
        
        Args:
            since_date: Fetch emails since this date (default: 7 days ago)
            max_results: Maximum number of emails to fetch (default: 100)
            
        Returns:
            List of email dictionaries with processed content
        """
        if not self.is_authenticated():
            logger.warning("Gmail service not authenticated")
            return []
        
        if since_date is None:
            since_date = timezone.now() - timedelta(days=7)
        
        try:
            # Build query for recent emails
            query = f'in:inbox after:{since_date.strftime("%Y/%m/%d")}'

            emails: List[Dict] = []
            remaining = max(0, int(max_results))
            page_token = None

            while remaining > 0:
                per_page = min(500, remaining)
                list_req = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=per_page,
                    includeSpamTrash=False,
                    labelIds=['INBOX'],
                    pageToken=page_token,
                    fields='messages(id,threadId),nextPageToken,resultSizeEstimate'
                )
                result = self._execute_with_retry(list_req)
                if not result:
                    break

                msg_refs = result.get('messages', [])
                logger.info(f"Fetched {len(msg_refs)} message refs (remaining target {remaining})")

                for ref in msg_refs:
                    email_data = self._process_message(ref['id']) if include_bodies else self._process_message_metadata(ref['id'])
                    if email_data:
                        emails.append(email_data)
                        remaining -= 1
                        if remaining <= 0:
                            break

                page_token = result.get('nextPageToken')
                if not page_token or remaining <= 0:
                    break

            return emails
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return []
    
    def _process_message(self, message_id: str) -> Optional[Dict]:
        """Process a single Gmail message and extract relevant data."""
        try:
            get_req = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full',
                fields='id,threadId,labelIds,payload/headers,payload/parts,payload/body,snippet'
            )
            message = self._execute_with_retry(get_req)
            
            headers = message['payload'].get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Extract email content
            body = self._extract_body(message['payload'])
            
            # Parse date
            date_str = header_dict.get('date', '')
            received_at = self._parse_date(date_str)
            
            email_data = {
                'id': message_id,
                'message_id': header_dict.get('message-id', message_id),
                'subject': header_dict.get('subject', 'No Subject'),
                'sender': header_dict.get('from', 'Unknown Sender'),
                'recipient': header_dict.get('to', self.user_email),
                'body': body,
                'date': received_at,
                'is_read': 'UNREAD' not in message.get('labelIds', []),
                'has_attachments': self._has_attachments(message['payload']),
                'labels': message.get('labelIds', []),
                'thread_id': message.get('threadId'),
                'platform': 'gmail'
            }
            
            return email_data
            
        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}")
            return None

    def _process_message_metadata(self, message_id: str) -> Optional[Dict]:
        """Process a Gmail message headers/snippet only (no body fetch)."""
        try:
            get_req = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'To', 'Date', 'Message-Id'],
                fields='id,threadId,labelIds,payload/headers,snippet'
            )
            message = self._execute_with_retry(get_req)

            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            date_str = header_dict.get('date', '')
            received_at = self._parse_date(date_str)

            return {
                'id': message_id,
                'message_id': header_dict.get('message-id', message_id),
                'subject': header_dict.get('subject', 'No Subject'),
                'sender': header_dict.get('from', 'Unknown Sender'),
                'recipient': header_dict.get('to', self.user_email),
                'body': '',
                'snippet': message.get('snippet', ''),
                'date': received_at,
                'is_read': 'UNREAD' not in message.get('labelIds', []),
                'has_attachments': False,
                'labels': message.get('labelIds', []),
                'thread_id': message.get('threadId'),
                'platform': 'gmail'
            }
        except Exception as e:
            logger.error(f"Failed to process message metadata {message_id}: {e}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body text from Gmail message payload (recursive, prefers text/plain; sanitizes HTML)."""
        def walk(part: Dict) -> str:
            # Dive into subparts first
            for p in part.get('parts', []) or []:
                text = walk(p)
                if text:
                    return text

            mime = part.get('mimeType', '')
            data = (part.get('body') or {}).get('data')
            if data and ('text/plain' in mime or 'text/html' in mime):
                try:
                    decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                except Exception:
                    decoded = ''
                if 'text/html' in mime and decoded:
                    # Basic HTML → text fallback
                    import re as _re
                    decoded = _re.sub(r'<script[^>]*>.*?</script>', '', decoded, flags=_re.DOTALL | _re.IGNORECASE)
                    decoded = _re.sub(r'<style[^>]*>.*?</style>', '', decoded, flags=_re.DOTALL | _re.IGNORECASE)
                    decoded = _re.sub(r'<[^>]+>', ' ', decoded)
                    decoded = ' '.join(decoded.split())
                return decoded
            return ''

        body = walk(payload) or ''
        return body[:5000]
    
    def _has_attachments(self, payload: Dict) -> bool:
        """Check if email has attachments."""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):
                    return True
                if 'parts' in part:
                    # Recursively check nested parts
                    if self._has_attachments(part):
                        return True
        return False

    def _execute_with_retry(self, request, max_retries: int = 3):
        """Execute a Google API request with basic exponential backoff on 429/5xx."""
        if not request:
            return None
        delay = 1.0
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                # googleapiclient HttpError has .resp.status
                status = None
                if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                    try:
                        status = int(e.resp.status)
                    except Exception:
                        status = None
                if status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    logger.warning(f"Gmail API transient error {status}; retrying in {delay:.1f}s...")
                    import time as _t
                    _t.sleep(delay)
                    delay *= 2
                    continue
                raise
            except Exception:
                if attempt < max_retries - 1:
                    import time as _t
                    _t.sleep(delay)
                    delay *= 2
                    continue
                raise
        return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime."""
        try:
            # Gmail provides RFC 2822 format dates
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return timezone.now()
    
    def setup_fyxerai_labels(self) -> Dict[str, str]:
        """
        Create FYXERAI categorization labels in Gmail.
        
        Returns:
            Dictionary mapping category names to label IDs
        """
        if not self.is_authenticated():
            raise Exception("Gmail service not authenticated")
        
        label_ids = {}
        
        try:
            # Get existing labels
            result = self.service.users().labels().list(userId='me').execute()
            existing_labels = {label['name']: label['id'] for label in result.get('labels', [])}
            
            # Create FYXERAI labels if they don't exist
            for category, config in self.FYXERAI_LABELS.items():
                label_name = config['name']
                
                if label_name in existing_labels:
                    label_ids[category] = existing_labels[label_name]
                    logger.info(f"Using existing label: {label_name}")
                else:
                    # Create new label
                    label_object = {
                        'name': label_name,
                        'messageListVisibility': config['messageListVisibility'],
                        'labelListVisibility': config['labelListVisibility'],
                        'color': config['color']
                    }
                    
                    created_label = self.service.users().labels().create(
                        userId='me',
                        body=label_object
                    ).execute()
                    
                    label_ids[category] = created_label['id']
                    logger.info(f"Created new label: {label_name}")
            
            return label_ids
            
        except HttpError as error:
            logger.error(f"Failed to setup labels: {error}")
            raise Exception(f"Label setup failed: {error}")
    
    def apply_label(self, message_id: str, category: str) -> bool:
        """
        Apply FYXERAI category label to an email.
        
        Args:
            message_id: Gmail message ID
            category: Category name (urgent, important, routine, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_authenticated():
            logger.warning("Gmail service not authenticated")
            return False
        
        try:
            # Get label ID for category
            cache_key = f"gmail_labels_{self.user_email}"
            label_ids = cache.get(cache_key)
            
            if not label_ids:
                label_ids = self.setup_fyxerai_labels()
                cache.set(cache_key, label_ids, 3600)  # Cache for 1 hour
            
            if category not in label_ids:
                logger.error(f"Unknown category: {category}")
                return False
            
            # Apply label to message
            req = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_ids[category]]}
            )
            self._execute_with_retry(req)
            
            logger.info(f"Applied {category} label to message {message_id}")
            return True
            
        except HttpError as error:
            logger.error(f"Failed to apply label: {error}")
            return False
        except Exception as e:
            logger.error(f"Label application error: {e}")
            return False
    
    def mark_important(self, message_id: str) -> bool:
        """Mark email as important in Gmail."""
        if not self.is_authenticated():
            return False
            
        try:
            req = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['IMPORTANT']}
            )
            self._execute_with_retry(req)
            return True
        except Exception as e:
            logger.error(f"Failed to mark important: {e}")
            return False
    
    def move_to_spam(self, message_id: str) -> bool:
        """Move email to spam folder."""
        if not self.is_authenticated():
            return False
            
        try:
            req = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': ['SPAM'],
                    'removeLabelIds': ['INBOX']
                }
            )
            self._execute_with_retry(req)
            return True
        except Exception as e:
            logger.error(f"Failed to move to spam: {e}")
            return False

    def batch_modify(self, message_ids: List[str], add_label_ids: List[str] = None, remove_label_ids: List[str] = None) -> bool:
        """Batch modify labels for multiple messages."""
        if not self.is_authenticated() or not message_ids:
            return False

    def start_watch(self, topic_name: str, label_ids: Optional[List[str]] = None, label_filter_action: str = 'include') -> Optional[Dict]:
        """Start Gmail Pub/Sub watch; saves historyId and expiration to the account."""
        if not self.is_authenticated() or not topic_name:
            return None
        body = {
            'topicName': topic_name,
            'labelIds': label_ids or ['INBOX'],
            'labelFilterAction': label_filter_action,
        }
        try:
            req = self.service.users().watch(userId='me', body=body)
            resp = self._execute_with_retry(req)
            if not resp:
                return None
            history_id = str(resp.get('historyId', ''))
            expiration_ms = resp.get('expiration')  # milliseconds since epoch
            from ..models import EmailAccount
            acct = EmailAccount.objects.filter(email_address=self.user_email, provider='gmail').first()
            if acct:
                if history_id:
                    acct.gmail_history_id = history_id
                if expiration_ms:
                    try:
                        from datetime import datetime, timezone as dt_tz
                        acct.gmail_watch_expiration = datetime.fromtimestamp(int(expiration_ms) / 1000.0, tz=dt_tz.utc)
                    except Exception:
                        pass
                acct.save(update_fields=['gmail_history_id', 'gmail_watch_expiration', 'updated_at'])
            return {'historyId': history_id, 'expiration': expiration_ms}
        except Exception as e:
            logger.error(f"Failed to start Gmail watch: {e}")
            return None

    def stop_watch(self) -> bool:
        """Stop Gmail Pub/Sub watch."""
        if not self.is_authenticated():
            return False
        try:
            req = self.service.users().stop(userId='me')
            self._execute_with_retry(req)
            return True
        except Exception as e:
            logger.error(f"Failed to stop Gmail watch: {e}")
            return False
        body = {
            'ids': message_ids,
            'addLabelIds': add_label_ids or [],
            'removeLabelIds': remove_label_ids or []
        }
        try:
            req = self.service.users().messages().batchModify(userId='me', body=body)
            self._execute_with_retry(req)
            return True
        except Exception as e:
            logger.error(f"Batch modify failed: {e}")
            return False
    
    def get_service_status(self) -> Dict:
        """Get Gmail service status and statistics."""
        status = {
            'authenticated': self.is_authenticated(),
            'user_email': self.user_email,
            'service_available': build is not None
        }
        
        if self.is_authenticated():
            try:
                # Get profile info
                prof_req = self.service.users().getProfile(userId='me')
                profile = self._execute_with_retry(prof_req)
                status.update({
                    'email_address': profile.get('emailAddress'),
                    'messages_total': profile.get('messagesTotal', 0),
                    'threads_total': profile.get('threadsTotal', 0),
                    'history_id': profile.get('historyId')
                })
                # Persist historyId for incremental sync if available
                try:
                    from ..models import EmailAccount
                    acct = EmailAccount.objects.filter(email_address=self.user_email, provider='gmail').first()
                    if acct and profile.get('historyId'):
                        acct.gmail_history_id = str(profile.get('historyId'))
                        acct.save(update_fields=['gmail_history_id', 'updated_at'])
                except Exception as _e:
                    logger.debug(f"Could not save gmail history id: {_e}")
            except Exception as e:
                logger.error(f"Failed to get profile: {e}")
        
        return status

    def get_unread_count(self) -> int:
        """Get unread message count in the inbox using Gmail search."""
        if not self.is_authenticated():
            return 0
        try:
            list_req = self.service.users().messages().list(
                userId='me', q='is:unread in:inbox', maxResults=1, fields='resultSizeEstimate'
            )
            result = self._execute_with_retry(list_req)
            # Gmail API includes resultSizeEstimate for queries
            return int(result.get('resultSizeEstimate', 0))
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0

    def fetch_history_since(self, start_history_id: str, max_results: int = 200) -> Tuple[List[Dict], Optional[str]]:
        """Fetch message changes since a historyId (new messages in INBOX).

        Returns (emails, latest_history_id).
        """
        if not self.is_authenticated() or not start_history_id:
            return [], None
        try:
            emails: List[Dict] = []
            page_token = None
            seen = 0
            latest_id = start_history_id
            while True:
                req = self.service.users().history().list(
                    userId='me', startHistoryId=start_history_id,
                    historyTypes=['messageAdded'], labelId='INBOX', pageToken=page_token,
                    fields='history(id,messagesAdded(message(id,threadId))),nextPageToken,historyId'
                )
                resp = self._execute_with_retry(req)
                if not resp:
                    break
                for h in resp.get('history', []) or []:
                    latest_id = str(h.get('id', latest_id))
                    for ma in h.get('messagesAdded', []) or []:
                        mid = ma.get('message', {}).get('id')
                        if not mid:
                            continue
                        data = self._process_message(mid)
                        if data:
                            emails.append(data)
                            seen += 1
                            if seen >= max_results:
                                return emails, latest_id
                page_token = resp.get('nextPageToken')
                if not page_token:
                    break
            return emails, latest_id
        except Exception as e:
            logger.error(f"Failed to fetch history since {start_history_id}: {e}")
            return [], None

    def create_draft(self, to: str, subject: str, body: str, reply_to_id: str = None) -> Optional[Dict]:
        """
        Create a draft email in Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            reply_to_id: Message ID if this is a reply
            
        Returns:
            Draft information or None if failed
        """
        if not self.is_authenticated():
            logger.warning("Gmail service not authenticated")
            return None
        
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['from'] = self.user_email
            message['subject'] = subject
            
            thread_id = None
            # Add reply headers and thread ID if this is a reply
            if reply_to_id:
                try:
                    get_req = self.service.users().messages().get(
                        userId='me', id=reply_to_id, fields='id,threadId,payload/headers'
                    )
                    original_message = self._execute_with_retry(get_req)
                    
                    original_headers = {h['name'].lower(): h['value'] 
                                     for h in original_message['payload'].get('headers', [])}
                    
                    # Set reply headers
                    if 'message-id' in original_headers:
                        message['In-Reply-To'] = original_headers['message-id']
                        message['References'] = original_headers['message-id']
                    
                    thread_id = original_message.get('threadId')
                except Exception as e:
                    logger.warning(f"Failed to set reply headers: {e}")
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Create draft
            draft_message = {'raw': raw_message}
            if thread_id:
                draft_message['threadId'] = thread_id
            draft_body = {'message': draft_message}

            create_req = self.service.users().drafts().create(userId='me', body=draft_body)
            draft = self._execute_with_retry(create_req)
            
            logger.info(f"Created draft {draft['id']} for {to}")
            return {
                'id': draft['id'],
                'message_id': draft['message']['id'],
                'thread_id': draft['message']['threadId']
            }
            
        except HttpError as error:
            logger.error(f"Gmail API error creating draft: {error}")
            return None
        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            return None
    
    def send_message(self, to: str, subject: str, body: str, reply_to_id: str = None) -> Optional[Dict]:
        """
        Send an email via Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            reply_to_id: Message ID if this is a reply
            
        Returns:
            Sent message information or None if failed
        """
        if not self.is_authenticated():
            logger.warning("Gmail service not authenticated")
            return None
        
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['from'] = self.user_email
            message['subject'] = subject
            
            # Add reply headers if this is a reply
            if reply_to_id:
                try:
                    original_message = self.service.users().messages().get(
                        userId='me', id=reply_to_id
                    ).execute()
                    
                    original_headers = {h['name'].lower(): h['value'] 
                                     for h in original_message['payload'].get('headers', [])}
                    
                    # Set reply headers
                    if 'message-id' in original_headers:
                        message['In-Reply-To'] = original_headers['message-id']
                        message['References'] = original_headers['message-id']
                    
                    message['Thread-ID'] = original_message.get('threadId')
                except Exception as e:
                    logger.warning(f"Failed to set reply headers: {e}")
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            message_body = {'raw': raw_message}
            if thread_id:
                message_body['threadId'] = thread_id
            
            send_req = self.service.users().messages().send(userId='me', body=message_body)
            sent_message = self._execute_with_retry(send_req)
            
            logger.info(f"Sent message {sent_message['id']} to {to}")
            return {
                'id': sent_message['id'],
                'thread_id': sent_message['threadId'],
                'label_ids': sent_message.get('labelIds', [])
            }
            
        except HttpError as error:
            logger.error(f"Gmail API error sending message: {error}")
            return None
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None
    
    def send_draft(self, draft_id: str) -> Optional[Dict]:
        """
        Send an existing draft email.
        
        Args:
            draft_id: Gmail draft ID
            
        Returns:
            Sent message information or None if failed
        """
        if not self.is_authenticated():
            logger.warning("Gmail service not authenticated")
            return None
        
        try:
            send_req = self.service.users().drafts().send(userId='me', body={'id': draft_id})
            sent_message = self._execute_with_retry(send_req)
            
            logger.info(f"Sent draft {draft_id}")
            return {
                'id': sent_message['id'],
                'thread_id': sent_message['threadId'],
                'label_ids': sent_message.get('labelIds', [])
            }
            
        except HttpError as error:
            logger.error(f"Gmail API error sending draft: {error}")
            return None
        except Exception as e:
            logger.error(f"Failed to send draft: {e}")
            return None


def get_gmail_service(user_email: str, scopes: Optional[List[str]] = None) -> GmailService:
    """Factory function to get Gmail service instance with optional scope minimization."""
    return GmailService(user_email, scopes=scopes)

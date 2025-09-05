"""
FYXERAI Unified Email Service
Clean implementation for Gmail and Outlook integration with AI processing
"""

import os
import json
import base64
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parsedate_to_datetime
import re

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import models
from core.models import EmailAccount
from core.services.gmail_service import get_gmail_service

# Gmail API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build as google_build
    from googleapiclient.errors import HttpError as GoogleHttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    Request = None
    Credentials = None
    InstalledAppFlow = None
    google_build = None
    GoogleHttpError = Exception

# Microsoft Graph API imports
try:
    import msal
    import requests
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False
    msal = None

# ML imports for classification
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    pipeline = None

import logging

logger = logging.getLogger(__name__)


class EmailNormalizer:
    """Normalizes email data from different sources into a unified format."""
    
    @staticmethod
    def extract_text_from_html(html_content: str) -> str:
        """Convert HTML to plain text (crude but effective)."""
        # Remove script and style elements
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text[:10000]  # Limit to 10k chars
    
    @staticmethod
    def normalize_email_data(source: str, raw_data: Dict) -> Dict:
        """Normalize email data from different sources."""
        normalized = {
            'source': source,
            'message_id': '',
            'thread_id': '',
            'subject': '',
            'from_': '',
            'to_': '',
            'date': timezone.now(),
            'snippet': '',
            'body_text': '',
            'has_attachments': False,
            'is_read': False,
            'labels': [],
            'categories': []
        }
        
        if source == 'gmail':
            normalized.update({
                'message_id': raw_data.get('id', ''),
                'thread_id': raw_data.get('thread_id', ''),
                'subject': raw_data.get('subject', ''),
                'from_': raw_data.get('sender', ''),
                'to_': raw_data.get('recipient', ''),
                'date': raw_data.get('date', timezone.now()),
                'snippet': raw_data.get('snippet', '')[:500],
                'body_text': raw_data.get('body', ''),
                'has_attachments': raw_data.get('has_attachments', False),
                'is_read': raw_data.get('is_read', False),
                'labels': raw_data.get('labels', [])
            })
        
        elif source == 'outlook':
            normalized.update({
                'message_id': raw_data.get('id', ''),
                'thread_id': raw_data.get('conversationId', ''),
                'subject': raw_data.get('subject', ''),
                'from_': raw_data.get('from', {}).get('emailAddress', {}).get('address', ''),
                'to_': ', '.join([r['emailAddress']['address'] for r in raw_data.get('toRecipients', [])]),
                'date': raw_data.get('receivedDateTime', timezone.now()),
                'snippet': raw_data.get('bodyPreview', '')[:500],
                'body_text': raw_data.get('body', {}).get('content', ''),
                'has_attachments': raw_data.get('hasAttachments', False),
                'is_read': raw_data.get('isRead', False),
                'categories': raw_data.get('categories', [])
            })
        
        # Clean body text if it's HTML
        if normalized['body_text'] and '<' in normalized['body_text']:
            normalized['body_text'] = EmailNormalizer.extract_text_from_html(normalized['body_text'])
        
        return normalized


class GmailIntegration:
    """Gmail API integration with proper OAuth flow."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels'
    ]
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.service = None
        self.credentials = None
        if GOOGLE_API_AVAILABLE:
            self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Gmail API service."""
        try:
            # Try to load existing credentials
            token_path = Path(f"tokens/gmail_{self.user_email}.json")
            
            if token_path.exists():
                self.credentials = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)
            
            # If no token file credentials, try loading from DB EmailAccount
            if not self.credentials:
                try:
                    account = EmailAccount.objects.filter(
                        email_address=self.user_email,
                        provider='gmail',
                        is_active=True,
                    ).first()
                    if account:
                        access_token = account.decrypt_token(account.access_token)
                        refresh_token = account.decrypt_token(account.refresh_token)
                        if refresh_token:
                            self.credentials = Credentials(
                                token=access_token or None,
                                refresh_token=refresh_token,
                                token_uri="https://oauth2.googleapis.com/token",
                                client_id=settings.GOOGLE_CLIENT_ID,
                                client_secret=settings.GOOGLE_CLIENT_SECRET,
                                scopes=self.SCOPES,
                            )
                except Exception as db_err:
                    logger.warning(f"Unable to load Gmail credentials from DB for {self.user_email}: {db_err}")
            
            # Refresh if needed
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                self._save_credentials()
                # Persist refreshed token back to DB if account exists
                try:
                    account = EmailAccount.objects.filter(
                        email_address=self.user_email,
                        provider='gmail',
                        is_active=True,
                    ).first()
                    if account:
                        account.access_token = account.encrypt_token(self.credentials.token)
                        if getattr(self.credentials, 'expiry', None):
                            # Ensure timezone-aware
                            expires_at = self.credentials.expiry
                            if timezone.is_naive(expires_at):
                                from datetime import timezone as dt_timezone
                                expires_at = expires_at.replace(tzinfo=dt_timezone.utc)
                            account.token_expires_at = expires_at
                        else:
                            account.token_expires_at = timezone.now() + timedelta(hours=1)
                        account.save()
                except Exception as save_err:
                    logger.warning(f"Failed to update Gmail token in DB for {self.user_email}: {save_err}")
            
            if self.credentials and self.credentials.valid:
                self.service = google_build('gmail', 'v1', credentials=self.credentials, cache_discovery=False)
                logger.info(f"Gmail service initialized for {self.user_email}")
            
            # If credentials loaded from DB but token file missing, write token file for CLI flows parity
            if self.credentials and not token_path.exists():
                self._save_credentials()
        except Exception as e:
            logger.error(f"Failed to initialize Gmail: {e}")
    
    def _save_credentials(self):
        """Save credentials to file."""
        if not self.credentials:
            return
        
        token_path = Path(f"tokens/gmail_{self.user_email}.json")
        token_path.parent.mkdir(exist_ok=True)
        
        token_data = {
            'token': self.credentials.token,
            'refresh_token': self.credentials.refresh_token,
            'token_uri': self.credentials.token_uri,
            'client_id': self.credentials.client_id,
            'client_secret': self.credentials.client_secret,
            'scopes': self.credentials.scopes
        }
        token_path.write_text(json.dumps(token_data))
    
    def get_oauth_flow(self):
        """Create OAuth flow for authorization."""
        if not GOOGLE_API_AVAILABLE:
            raise Exception("Google API client not installed")
        
        creds_path = Path("credentials.json")
        if not creds_path.exists():
            # Use from settings
            client_config = {
                "installed": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, self.SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), self.SCOPES)
        
        return flow
    
    def fetch_messages(self, query: str = "newer_than:7d", max_results: int = 100) -> List[Dict]:
        """Fetch messages from Gmail with pagination and partial responses."""
        if not self.service:
            logger.warning("Gmail service not initialized")
            return []
        
        try:
            messages: List[Dict] = []
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

                for msg_ref in result.get('messages', []) or []:
                    get_req = self.service.users().messages().get(
                        userId='me', id=msg_ref['id'], format='full',
                        fields='id,threadId,labelIds,snippet,payload/headers,payload/parts,payload/body'
                    )
                    msg = self._execute_with_retry(get_req)

                    headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
                    body_text = self._extract_body(msg.get('payload', {}))

                    messages.append({
                        'id': msg.get('id'),
                        'thread_id': msg.get('threadId'),
                        'subject': headers.get('subject', ''),
                        'sender': headers.get('from', ''),
                        'recipient': headers.get('to', ''),
                        'date': parsedate_to_datetime(headers.get('date', '')) if headers.get('date') else timezone.now(),
                        'snippet': msg.get('snippet', ''),
                        'body': body_text,
                        'has_attachments': self._has_attachments(msg.get('payload', {})),
                        'is_read': 'UNREAD' not in msg.get('labelIds', []),
                        'labels': msg.get('labelIds', [])
                    })
                    remaining -= 1
                    if remaining <= 0:
                        break

                page_token = result.get('nextPageToken')
                if not page_token or remaining <= 0:
                    break

            return messages
            
        except Exception as e:
            logger.error(f"Failed to fetch Gmail messages: {e}")
            return []
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract text from message payload."""
        def walk_parts(part):
            if part.get('parts'):
                for p in part['parts']:
                    text = walk_parts(p)
                    if text:
                        return text
            
            mime_type = part.get('mimeType', '')
            if 'text/plain' in mime_type or 'text/html' in mime_type:
                data = part.get('body', {}).get('data')
                if data:
                    text = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                    if 'text/html' in mime_type:
                        text = EmailNormalizer.extract_text_from_html(text)
                    return text
            return ''
        
        return walk_parts(payload) or ''
    
    def _has_attachments(self, payload: Dict) -> bool:
        """Check if message has attachments."""
        if payload.get('parts'):
            for part in payload['parts']:
                if part.get('filename'):
                    return True
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
            except GoogleHttpError as e:
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
    
    def create_label(self, label_name: str, color: Dict = None) -> str:
        """Create a Gmail label."""
        if not self.service:
            return None
        
        try:
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            if color:
                label_object['color'] = color
            
            req = self.service.users().labels().create(userId='me', body=label_object)
            result = self._execute_with_retry(req)
            
            return result['id']
        except Exception as e:
            logger.error(f"Failed to create label: {e}")
            return None
    
    def apply_label(self, message_id: str, label_ids: List[str]) -> bool:
        """Apply labels to a message."""
        if not self.service:
            return False
        
        try:
            req = self.service.users().messages().modify(
                userId='me', id=message_id, body={'addLabelIds': label_ids}
            )
            self._execute_with_retry(req)
            return True
        except Exception as e:
            logger.error(f"Failed to apply label: {e}")
            return False


class OutlookIntegration:
    """Microsoft Graph API integration for Outlook."""
    
    SCOPES = ['Mail.Read', 'Mail.ReadWrite']
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.token = None
        self.client_id = settings.MICROSOFT_CLIENT_ID if hasattr(settings, 'MICROSOFT_CLIENT_ID') else None
        self.tenant = 'common'
        
        if MSAL_AVAILABLE and self.client_id:
            self._initialize_auth()
    
    def _initialize_auth(self):
        """Initialize MSAL authentication."""
        try:
            # Try to load existing token
            token_path = Path(f"tokens/outlook_{self.user_email}.json")
            if token_path.exists():
                token_data = json.loads(token_path.read_text())
                self.token = token_data.get('access_token')
        except Exception as e:
            logger.error(f"Failed to load Outlook token: {e}")
    
    def get_device_flow(self):
        """Get device flow for authentication."""
        if not MSAL_AVAILABLE:
            raise Exception("MSAL not installed")
        
        app = msal.PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant}"
        )
        
        flow = app.initiate_device_flow(scopes=self.SCOPES)
        return flow
    
    def acquire_token_by_device_flow(self, flow):
        """Complete device flow authentication."""
        if not MSAL_AVAILABLE:
            raise Exception("MSAL not installed")
        
        app = msal.PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant}"
        )
        
        result = app.acquire_token_by_device_flow(flow)
        
        if 'access_token' in result:
            self.token = result['access_token']
            self._save_token(result)
            return True
        
        return False
    
    def _save_token(self, token_data):
        """Save token to file."""
        token_path = Path(f"tokens/outlook_{self.user_email}.json")
        token_path.parent.mkdir(exist_ok=True)
        token_path.write_text(json.dumps(token_data))
    
    def fetch_messages(self, top: int = 50) -> List[Dict]:
        """Fetch messages from Outlook/Microsoft 365."""
        if not self.token:
            logger.warning("Outlook not authenticated")
            return []
        
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            url = f'https://graph.microsoft.com/v1.0/me/messages?$top={top}'
            
            messages = []
            while url:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for msg in data.get('value', []):
                    messages.append({
                        'id': msg['id'],
                        'conversationId': msg.get('conversationId'),
                        'subject': msg.get('subject', ''),
                        'from': msg.get('from', {}),
                        'toRecipients': msg.get('toRecipients', []),
                        'receivedDateTime': msg.get('receivedDateTime'),
                        'bodyPreview': msg.get('bodyPreview', ''),
                        'body': msg.get('body', {}),
                        'hasAttachments': msg.get('hasAttachments', False),
                        'isRead': msg.get('isRead', False),
                        'categories': msg.get('categories', [])
                    })
                
                url = data.get('@odata.nextLink')
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to fetch Outlook messages: {e}")
            return []
    
    def set_categories(self, message_id: str, categories: List[str]) -> bool:
        """Set categories on an Outlook message."""
        if not self.token:
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.patch(
                f'https://graph.microsoft.com/v1.0/me/messages/{message_id}',
                headers=headers,
                json={'categories': categories},
                timeout=30
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set categories: {e}")
            return False


class EmailClassifier:
    """Zero-shot email classification using local models."""
    
    DEFAULT_LABELS = [
        "Urgent/Critical",
        "Important/Action Required",
        "Routine/Informational",
        "Promotional/Marketing",
        "Spam/Junk",
        "Personal",
        "Meeting/Calendar",
        "Support/Customer Service",
        "Invoice/Billing",
        "Project Update"
    ]
    
    def __init__(self, labels: List[str] = None):
        self.labels = labels or self.DEFAULT_LABELS
        self.classifier = None
        
        if TRANSFORMERS_AVAILABLE:
            try:
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli"
                )
                logger.info("Email classifier initialized")
            except Exception as e:
                logger.error(f"Failed to load classification model: {e}")
    
    def classify(self, text: str, multi_label: bool = True, threshold: float = 0.35) -> List[str]:
        """Classify email text into categories."""
        if not self.classifier:
            # Fallback to keyword-based classification
            return self._keyword_classify(text)
        
        try:
            # Truncate text for efficiency
            text = text[:4000]
            
            result = self.classifier(
                text,
                candidate_labels=self.labels,
                multi_label=multi_label
            )
            
            # Filter by threshold and return top categories
            scored = list(zip(result['labels'], result['scores']))
            categories = [label for label, score in scored if score >= threshold][:3]
            
            return categories if categories else [scored[0][0]]
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return self._keyword_classify(text)
    
    def _keyword_classify(self, text: str) -> List[str]:
        """Fallback keyword-based classification."""
        text_lower = text.lower()
        categories = []
        
        # Simple keyword matching
        if any(word in text_lower for word in ['urgent', 'asap', 'critical', 'emergency']):
            categories.append("Urgent/Critical")
        elif any(word in text_lower for word in ['meeting', 'calendar', 'schedule', 'appointment']):
            categories.append("Meeting/Calendar")
        elif any(word in text_lower for word in ['invoice', 'payment', 'billing']):
            categories.append("Invoice/Billing")
        elif any(word in text_lower for word in ['unsubscribe', 'promotion', 'deal', 'offer']):
            categories.append("Promotional/Marketing")
        else:
            categories.append("Routine/Informational")
        
        return categories


class EmailSummarizer:
    """Email summarization and draft generation using LLMs."""
    
    def __init__(self, openai_api_key: str = None):
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        
    def summarize(self, email_content: str, max_length: int = 150) -> Dict:
        """Generate email summary with action items."""
        # For now, a simple extractive summary
        # In production, this would call OpenAI or another LLM
        
        lines = email_content.split('\n')
        summary_lines = []
        action_items = []
        
        for line in lines[:10]:  # First 10 lines
            line = line.strip()
            if not line:
                continue
            
            # Detect action items
            if any(keyword in line.lower() for keyword in ['please', 'need', 'require', 'must', 'should']):
                action_items.append(line[:100])
            
            if len(summary_lines) < 3:
                summary_lines.append(line[:150])
        
        return {
            'summary': ' '.join(summary_lines)[:max_length],
            'action_items': action_items[:3],
            'key_points': summary_lines[:3]
        }
    
    def generate_draft_reply(self, email_content: str, context: Dict = None) -> str:
        """Generate a draft reply to an email."""
        # Simple template-based reply for now
        # In production, this would use OpenAI or another LLM
        
        reply_template = """Thank you for your email.

I have received your message and will review it shortly. 

{response}

Best regards"""
        
        # Analyze email for appropriate response
        email_lower = email_content.lower()
        
        if 'meeting' in email_lower:
            response = "I will check my calendar and get back to you with my availability."
        elif 'urgent' in email_lower:
            response = "I understand the urgency and will prioritize this matter."
        elif 'invoice' in email_lower:
            response = "I will review the invoice and process it accordingly."
        else:
            response = "I will respond with more details soon."
        
        return reply_template.format(response=response)


class UnifiedEmailService:
    """Unified service for managing emails from multiple providers."""
    
    def __init__(self, db_path: str = "emails.db"):
        self.db_path = db_path
        self.normalizer = EmailNormalizer()
        self.classifier = EmailClassifier()
        self.summarizer = EmailSummarizer()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for email storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                message_id TEXT UNIQUE NOT NULL,
                thread_id TEXT,
                subject TEXT,
                from_address TEXT,
                to_address TEXT,
                date TIMESTAMP,
                snippet TEXT,
                body_text TEXT,
                has_attachments BOOLEAN,
                is_read BOOLEAN,
                labels TEXT,
                categories TEXT,
                summary TEXT,
                action_items TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def ingest_gmail(self, user_email: str, query: str = "newer_than:7d") -> int:
        """Ingest emails from Gmail (uses unified GmailService)."""
        svc = get_gmail_service(user_email, scopes=['https://www.googleapis.com/auth/gmail.readonly'])
        if not svc or not svc.is_authenticated():
            logger.warning("Gmail service not authenticated for ingestion")
            return 0
        # Map common query to since_date (simple support for newer_than:Nd)
        since_days = 7
        try:
            import re as _re
            m = _re.search(r'newer_than:(\d+)d', query)
            if m:
                since_days = int(m.group(1))
        except Exception:
            pass
        from django.utils import timezone as _tz
        from datetime import timedelta as _td
        messages = svc.fetch_emails(since_date=_tz.now() - _td(days=since_days), max_results=200)
        
        count = 0
        for msg in messages:
            normalized = self.normalizer.normalize_email_data('gmail', msg)
            if self._save_email(normalized):
                count += 1
        
        logger.info(f"Ingested {count} Gmail messages")
        return count
    
    def ingest_outlook(self, user_email: str, top: int = 50) -> int:
        """Ingest emails from Outlook."""
        outlook = OutlookIntegration(user_email)
        messages = outlook.fetch_messages(top=top)
        
        count = 0
        for msg in messages:
            normalized = self.normalizer.normalize_email_data('outlook', msg)
            if self._save_email(normalized):
                count += 1
        
        logger.info(f"Ingested {count} Outlook messages")
        return count
    
    def _save_email(self, email_data: Dict) -> bool:
        """Save email to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO emails (
                    source, message_id, thread_id, subject,
                    from_address, to_address, date, snippet,
                    body_text, has_attachments, is_read,
                    labels, categories
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email_data['source'],
                email_data['message_id'],
                email_data['thread_id'],
                email_data['subject'],
                email_data['from_'],
                email_data['to_'],
                email_data['date'],
                email_data['snippet'],
                email_data['body_text'],
                email_data['has_attachments'],
                email_data['is_read'],
                json.dumps(email_data['labels']),
                json.dumps(email_data.get('categories', []))
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save email: {e}")
            return False
    
    def classify_emails(self, limit: int = 100) -> int:
        """Classify unclassified emails in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get unclassified emails
        cursor.execute("""
            SELECT id, subject, snippet, body_text 
            FROM emails 
            WHERE categories = '[]' OR categories IS NULL
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        count = 0
        
        for row in rows:
            email_id, subject, snippet, body = row
            
            # Combine text for classification
            text = f"{subject or ''}\n{snippet or ''}\n{body or ''}"
            
            # Classify
            categories = self.classifier.classify(text)
            
            # Update database
            cursor.execute("""
                UPDATE emails 
                SET categories = ? 
                WHERE id = ?
            """, (json.dumps(categories), email_id))
            
            count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"Classified {count} emails")
        return count
    
    def summarize_emails(self, limit: int = 50) -> int:
        """Generate summaries for emails."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get unsummarized emails
        cursor.execute("""
            SELECT id, subject, body_text 
            FROM emails 
            WHERE summary IS NULL OR summary = ''
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        count = 0
        
        for row in rows:
            email_id, subject, body = row
            
            # Generate summary
            content = f"{subject or ''}\n{body or ''}"
            summary_data = self.summarizer.summarize(content)
            
            # Update database
            cursor.execute("""
                UPDATE emails 
                SET summary = ?, action_items = ?
                WHERE id = ?
            """, (
                summary_data['summary'],
                json.dumps(summary_data['action_items']),
                email_id
            ))
            
            count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"Summarized {count} emails")
        return count
    
    def generate_draft(self, email_id: int) -> str:
        """Generate a draft reply for an email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT subject, body_text, from_address 
            FROM emails 
            WHERE id = ?
        """, (email_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        subject, body, from_addr = row
        content = f"Subject: {subject}\nFrom: {from_addr}\n\n{body}"
        
        return self.summarizer.generate_draft_reply(content)
    
    def apply_labels_to_source(self, email_id: int) -> bool:
        """Apply categories back to the email source (Gmail/Outlook)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source, message_id, categories, from_address
            FROM emails 
            WHERE id = ?
        """, (email_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False
        
        source, message_id, categories_json, from_addr = row
        categories = json.loads(categories_json) if categories_json else []
        
        if not categories:
            return False
        
        # Apply to source
        if source == 'gmail':
            # Extract email from from_address
            email = from_addr.split('<')[-1].strip('>') if '<' in from_addr else from_addr
            gmail = GmailIntegration(email)
            
            # Create and apply labels
            for category in categories:
                label_name = f"FYXERAI/{category}"
                label_id = gmail.create_label(label_name)
                if label_id:
                    gmail.apply_label(message_id, [label_id])
            
            return True
            
        elif source == 'outlook':
            email = from_addr.split('<')[-1].strip('>') if '<' in from_addr else from_addr
            outlook = OutlookIntegration(email)
            
            # Set categories
            return outlook.set_categories(message_id, categories)
        
        return False
    
    def get_email_stats(self) -> Dict:
        """Get statistics about processed emails."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total emails
        cursor.execute("SELECT COUNT(*) FROM emails")
        stats['total'] = cursor.fetchone()[0]
        
        # By source
        cursor.execute("SELECT source, COUNT(*) FROM emails GROUP BY source")
        stats['by_source'] = dict(cursor.fetchall())
        
        # Classified
        cursor.execute("SELECT COUNT(*) FROM emails WHERE categories != '[]' AND categories IS NOT NULL")
        stats['classified'] = cursor.fetchone()[0]
        
        # Summarized
        cursor.execute("SELECT COUNT(*) FROM emails WHERE summary IS NOT NULL AND summary != ''")
        stats['summarized'] = cursor.fetchone()[0]
        
        # Category distribution
        cursor.execute("SELECT categories FROM emails WHERE categories IS NOT NULL AND categories != '[]'")
        category_counts = {}
        for row in cursor.fetchall():
            categories = json.loads(row[0])
            for cat in categories:
                category_counts[cat] = category_counts.get(cat, 0) + 1
        stats['categories'] = category_counts
        
        conn.close()
        
        return stats

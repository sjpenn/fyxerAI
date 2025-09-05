from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from cryptography.fernet import Fernet
import base64
import hashlib
from django.conf import settings
import json


class User(AbstractUser):
    """Extended user model for FyxerAI-GEDS"""
    
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_premium = models.BooleanField(default=False)
    timezone = models.CharField(max_length=50, default='UTC')
    
    def __str__(self):
        return self.username


class EmailAccount(models.Model):
    """OAuth-connected Gmail/Outlook accounts"""
    
    PROVIDER_CHOICES = [
        ('gmail', 'Gmail'),
        ('outlook', 'Outlook'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_accounts')
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES)
    email_address = models.EmailField()
    display_name = models.CharField(max_length=255, blank=True)
    
    # OAuth tokens (encrypted)
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expires_at = models.DateTimeField()
    
    # Account metadata
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_enabled = models.BooleanField(default=True)
    
    # Gmail incremental sync (optional)
    gmail_history_id = models.CharField(max_length=50, blank=True)
    gmail_watch_expiration = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'email_address']
        indexes = [
            models.Index(fields=['user', 'provider']),
            models.Index(fields=['email_address']),
        ]
    
    def __str__(self):
        return f"{self.email_address} ({self.provider})"
    
    def encrypt_token(self, token):
        """Encrypt token before storing"""
        if not token:
            return ''
        
        # Derive a stable Fernet key from SECRET_KEY
        key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        fernet = Fernet(fernet_key)
        return fernet.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token):
        """Decrypt token for use"""
        if not encrypted_token:
            return ''
        
        # Use same stable key as encryption
        key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        fernet = Fernet(fernet_key)
        return fernet.decrypt(encrypted_token.encode()).decode()


class EmailMessage(models.Model):
    """Individual emails with categories and metadata"""
    
    CATEGORY_CHOICES = [
        ('urgent', 'Urgent'),
        ('important', 'Important'),
        ('newsletter', 'Newsletter'),
        ('promotion', 'Promotion'),
        ('social', 'Social'),
        ('notification', 'Notification'),
        ('spam', 'Spam'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    # Email identification
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='messages')
    message_id = models.CharField(max_length=255)  # Provider's message ID
    thread_id = models.CharField(max_length=255, blank=True)
    
    # Email content
    subject = models.TextField()
    sender_email = models.EmailField()
    sender_name = models.CharField(max_length=255, blank=True)
    recipient_emails = models.JSONField(default=list)
    cc_emails = models.JSONField(default=list)
    bcc_emails = models.JSONField(default=list)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    
    # AI categorization and metadata
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    ai_confidence = models.FloatField(default=0.0)  # AI confidence score (0-1)
    manual_override = models.BooleanField(default=False)  # User manually changed category
    
    # Email status
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    has_attachments = models.BooleanField(default=False)
    
    # AI-generated responses
    has_draft_reply = models.BooleanField(default=False)
    draft_reply_content = models.TextField(blank=True)
    draft_generated_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    received_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['account', 'message_id']
        indexes = [
            models.Index(fields=['account', 'category']),
            models.Index(fields=['account', 'received_at']),
            models.Index(fields=['sender_email']),
            models.Index(fields=['category', 'priority']),
        ]
        ordering = ['-received_at']
    
    def __str__(self):
        if len(self.subject) > 50:
            return f"{self.subject[:50]}... from {self.sender_email}"
        return f"{self.subject} from {self.sender_email}"


class UserPreference(models.Model):
    """User tone profiles and category settings"""
    
    TONE_CHOICES = [
        ('professional', 'Professional'),
        ('friendly', 'Friendly'),
        ('casual', 'Casual'),
        ('formal', 'Formal'),
        ('concise', 'Concise'),
        ('detailed', 'Detailed'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # Email tone and response preferences
    default_tone = models.CharField(max_length=20, choices=TONE_CHOICES, default='professional')
    signature = models.TextField(blank=True)
    auto_categorize = models.BooleanField(default=True)
    auto_generate_drafts = models.BooleanField(default=True)
    
    # Category preferences (JSON field for flexible configuration)
    category_rules = models.JSONField(default=dict)  # Custom rules for categorization
    notification_settings = models.JSONField(default=dict)  # Which categories trigger notifications
    
    # AI behavior settings
    ai_confidence_threshold = models.FloatField(default=0.7)  # Minimum confidence for auto-categorization
    learning_enabled = models.BooleanField(default=True)  # Allow AI to learn from user corrections
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} preferences"
    
    def get_category_rule(self, sender_email):
        """Get custom category rule for a specific sender"""
        return self.category_rules.get(sender_email, {})
    
    def set_category_rule(self, sender_email, category, priority='medium'):
        """Set custom category rule for a sender"""
        if not self.category_rules:
            self.category_rules = {}
        
        self.category_rules[sender_email] = {
            'category': category,
            'priority': priority,
            'created_at': timezone.now().isoformat()
        }
        self.save()


class Meeting(models.Model):
    """Meeting recordings and transcripts stored in S3"""
    
    PLATFORM_CHOICES = [
        ('zoom', 'Zoom'),
        ('teams', 'Microsoft Teams'),
        ('meet', 'Google Meet'),
        ('webex', 'Cisco Webex'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meetings')
    
    # Meeting details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    meeting_url = models.URLField(blank=True)
    external_meeting_id = models.CharField(max_length=255, blank=True)  # Platform's meeting ID
    
    # Timing
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    # Participants
    organizer_email = models.EmailField()
    participants = models.JSONField(default=list)  # List of participant emails/names
    
    # Recording and transcription
    recording_url = models.URLField(blank=True)  # S3 URL for recording
    transcript_url = models.URLField(blank=True)  # S3 URL for transcript
    has_recording = models.BooleanField(default=False)
    has_transcript = models.BooleanField(default=False)
    
    # AI-generated content
    summary = models.TextField(blank=True)
    action_items = models.JSONField(default=list)  # List of action items
    key_topics = models.JSONField(default=list)  # Key topics discussed
    follow_up_emails = models.JSONField(default=list)  # Suggested follow-up emails
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    transcription_completed = models.BooleanField(default=False)
    summary_generated = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'scheduled_start']),
            models.Index(fields=['platform', 'status']),
            models.Index(fields=['external_meeting_id']),
        ]
        ordering = ['-scheduled_start']
    
    def __str__(self):
        return f"{self.title} - {self.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration_minutes(self):
        """Calculate meeting duration in minutes"""
        if self.actual_start and self.actual_end:
            delta = self.actual_end - self.actual_start
            return int(delta.total_seconds() / 60)
        elif self.scheduled_start and self.scheduled_end:
            delta = self.scheduled_end - self.scheduled_start
            return int(delta.total_seconds() / 60)
        return 0

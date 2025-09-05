# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-08-19-django-postgresql-setup/spec.md

> Created: 2025-08-19
> Version: 1.0.0

## Database Changes

### New Tables

#### Custom User Table (extends Django's AbstractUser)
- Extends Django's built-in User model with email assistant specific fields
- Supports multiple email account connections per user
- Includes timezone and preferences for email processing

#### EmailAccount Table
- Stores OAuth-connected Gmail and Outlook account information
- Encrypted token storage for secure API access
- Provider-specific configuration and metadata

#### EmailMessage Table  
- Central storage for email metadata and categorization
- Optimized for fast querying across multiple accounts
- Supports AI categorization and draft generation workflows

#### UserPreference Table
- Stores AI tone profiles and category preferences
- JSON fields for flexible preference storage
- One-to-one relationship with User model

## Database Schema Specifications

### Custom User Model
```python
# models.py - Custom User extending AbstractUser
class User(AbstractUser):
    timezone = models.CharField(max_length=50, default='UTC')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]
```

### EmailAccount Model
```python
class EmailAccount(models.Model):
    PROVIDER_CHOICES = [
        ('gmail', 'Gmail'),
        ('outlook', 'Outlook'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    email_address = models.EmailField()
    display_name = models.CharField(max_length=255, blank=True)
    
    # OAuth token storage (will be encrypted)
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expires_at = models.DateTimeField()
    
    # Provider-specific fields
    provider_user_id = models.CharField(max_length=255)
    provider_metadata = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_accounts'
        unique_together = ['user', 'provider', 'email_address']
        indexes = [
            models.Index(fields=['user', 'provider']),
            models.Index(fields=['email_address']),
            models.Index(fields=['token_expires_at']),
            models.Index(fields=['is_active']),
        ]
```

### EmailMessage Model
```python
class EmailMessage(models.Model):
    CATEGORY_CHOICES = [
        ('to_respond', 'To Respond'),
        ('fyi', 'FYI'),
        ('marketing', 'Marketing'),
        ('spam', 'Spam'),
        ('uncategorized', 'Uncategorized'),
    ]
    
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='messages')
    message_id = models.CharField(max_length=255)  # Provider's message ID
    thread_id = models.CharField(max_length=255, blank=True)  # Provider's thread ID
    
    # Email metadata
    subject = models.CharField(max_length=998, blank=True)  # RFC 5322 limit
    sender = models.EmailField()
    recipients = models.JSONField(default=list)  # List of recipient emails
    date_sent = models.DateTimeField()
    date_received = models.DateTimeField(auto_now_add=True)
    
    # AI processing
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='uncategorized')
    ai_confidence = models.FloatField(null=True, blank=True)  # 0.0-1.0
    
    # Draft management
    has_ai_draft = models.BooleanField(default=False)
    draft_generated_at = models.DateTimeField(null=True, blank=True)
    
    # Email content flags
    has_attachments = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    # Metadata and processing
    provider_labels = models.JSONField(default=list)  # Gmail labels or Outlook categories
    processing_metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_messages'
        unique_together = ['account', 'message_id']
        indexes = [
            models.Index(fields=['account', 'category']),
            models.Index(fields=['account', 'date_sent']),
            models.Index(fields=['sender']),
            models.Index(fields=['category', 'date_received']),
            models.Index(fields=['has_ai_draft']),
            models.Index(fields=['is_read', 'category']),
        ]
```

### UserPreference Model
```python
class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # AI tone profile
    tone_profile = models.JSONField(default=dict, blank=True)  # Learned from sent emails
    
    # Category preferences
    enabled_categories = models.JSONField(
        default=lambda: ['to_respond', 'fyi', 'marketing', 'spam']
    )
    category_rules = models.JSONField(default=dict, blank=True)  # Custom rules
    
    # UI preferences
    theme = models.CharField(max_length=10, choices=[('dark', 'Dark'), ('light', 'Light')], default='dark')
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Integration settings
    slack_notifications = models.BooleanField(default=False)
    teams_notifications = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
```

## Migration Strategy

### Initial Migration (0001_initial.py)
```python
# Migration creates all tables with proper indexes and constraints
# Includes data migration for existing Django User table if needed
operations = [
    # Custom User model setup
    migrations.CreateModel(name='User', ...),
    
    # Core email models
    migrations.CreateModel(name='EmailAccount', ...),
    migrations.CreateModel(name='EmailMessage', ...),
    migrations.CreateModel(name='UserPreference', ...),
    
    # Indexes for performance
    migrations.AddIndex(...),
    
    # Foreign key constraints
    migrations.AddConstraint(...),
]
```

## Performance Considerations

### Indexing Strategy
- Composite indexes on frequently queried field combinations (user+provider, account+category)
- Single field indexes on high-cardinality fields (email_address, message_id)
- Partial indexes for boolean fields to optimize query performance

### Query Optimization
- EmailMessage queries optimized for inbox views with category filtering
- EmailAccount queries optimized for multi-account user scenarios  
- Foreign key relationships designed to minimize N+1 query problems

### Data Integrity
- Unique constraints prevent duplicate email accounts per user
- Foreign key constraints maintain referential integrity
- JSON field validation for structured data storage

## Rationale

### Custom User Model
Using Django's AbstractUser allows extension while maintaining compatibility with Django's authentication system. Early implementation prevents complex migrations later.

### Encrypted Token Storage
OAuth tokens stored as encrypted fields provide security while maintaining database query capabilities. Separate access/refresh token fields support OAuth 2.0 token refresh workflows.

### Optimized Email Storage
EmailMessage model balances normalized design with query performance. JSON fields provide flexibility for provider-specific metadata while maintaining structured query capabilities.

### Flexible Preferences System
JSON-based preferences allow rapid iteration on AI features without schema changes while maintaining query performance for common operations.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailAccount, EmailMessage, UserPreference, Meeting


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model"""
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_premium', 'is_staff', 'date_joined')
    list_filter = ('is_premium', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('FyxerAI Settings', {
            'fields': ('is_premium', 'timezone'),
        }),
    )


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    """Admin interface for EmailAccount model"""
    
    list_display = ('email_address', 'provider', 'user', 'is_active', 'last_sync', 'created_at')
    list_filter = ('provider', 'is_active', 'sync_enabled', 'created_at')
    search_fields = ('email_address', 'display_name', 'user__username')
    readonly_fields = ('access_token', 'refresh_token', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Account Info', {
            'fields': ('user', 'provider', 'email_address', 'display_name'),
        }),
        ('OAuth Tokens', {
            'fields': ('access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',),
        }),
        ('Settings', {
            'fields': ('is_active', 'sync_enabled', 'last_sync'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    """Admin interface for EmailMessage model"""
    
    list_display = ('subject_short', 'sender_email', 'category', 'priority', 'is_read', 'received_at')
    list_filter = ('category', 'priority', 'is_read', 'is_starred', 'manual_override', 'account__provider')
    search_fields = ('subject', 'sender_email', 'sender_name', 'body_text')
    readonly_fields = ('message_id', 'thread_id', 'ai_confidence', 'created_at', 'updated_at')
    date_hierarchy = 'received_at'
    
    def subject_short(self, obj):
        return obj.subject[:50] + "..." if len(obj.subject) > 50 else obj.subject
    subject_short.short_description = 'Subject'
    
    fieldsets = (
        ('Email Info', {
            'fields': ('account', 'message_id', 'thread_id', 'subject', 'received_at'),
        }),
        ('Sender/Recipients', {
            'fields': ('sender_email', 'sender_name', 'recipient_emails', 'cc_emails', 'bcc_emails'),
        }),
        ('Content', {
            'fields': ('body_text', 'body_html', 'has_attachments'),
            'classes': ('collapse',),
        }),
        ('AI Classification', {
            'fields': ('category', 'priority', 'ai_confidence', 'manual_override'),
        }),
        ('Status', {
            'fields': ('is_read', 'is_starred', 'is_archived'),
        }),
        ('AI Responses', {
            'fields': ('has_draft_reply', 'draft_reply_content', 'draft_generated_at'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for UserPreference model"""
    
    list_display = ('user', 'default_tone', 'auto_categorize', 'auto_generate_drafts', 'ai_confidence_threshold')
    list_filter = ('default_tone', 'auto_categorize', 'auto_generate_drafts', 'learning_enabled')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',),
        }),
        ('Email Preferences', {
            'fields': ('default_tone', 'signature', 'auto_categorize', 'auto_generate_drafts'),
        }),
        ('AI Settings', {
            'fields': ('ai_confidence_threshold', 'learning_enabled'),
        }),
        ('Advanced', {
            'fields': ('category_rules', 'notification_settings'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    """Admin interface for Meeting model"""
    
    list_display = ('title', 'platform', 'status', 'scheduled_start', 'organizer_email', 'has_recording')
    list_filter = ('platform', 'status', 'has_recording', 'has_transcript', 'transcription_completed')
    search_fields = ('title', 'description', 'organizer_email', 'external_meeting_id')
    readonly_fields = ('external_meeting_id', 'duration_minutes', 'created_at', 'updated_at')
    date_hierarchy = 'scheduled_start'
    
    fieldsets = (
        ('Meeting Info', {
            'fields': ('user', 'title', 'description', 'platform', 'external_meeting_id'),
        }),
        ('Timing', {
            'fields': ('scheduled_start', 'scheduled_end', 'actual_start', 'actual_end', 'duration_minutes'),
        }),
        ('Participants', {
            'fields': ('organizer_email', 'participants'),
        }),
        ('URLs', {
            'fields': ('meeting_url', 'recording_url', 'transcript_url'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('status', 'has_recording', 'has_transcript', 'transcription_completed', 'summary_generated'),
        }),
        ('AI Content', {
            'fields': ('summary', 'action_items', 'key_topics', 'follow_up_emails'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

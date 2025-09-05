from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import EmailAccount, EmailMessage, UserPreference, Meeting

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'is_premium', 'timezone', 'date_joined', 'password')
        read_only_fields = ('id', 'date_joined')
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class EmailAccountSerializer(serializers.ModelSerializer):
    """Serializer for EmailAccount model"""
    
    class Meta:
        model = EmailAccount
        fields = ('id', 'provider', 'email_address', 'display_name', 
                 'is_active', 'sync_enabled', 'last_sync', 'created_at')
        read_only_fields = ('id', 'last_sync', 'created_at')
    
    def validate_email_address(self, value):
        """Ensure email address is unique for this user"""
        user = self.context['request'].user
        if EmailAccount.objects.filter(user=user, email_address=value).exists():
            raise serializers.ValidationError("This email address is already connected to your account.")
        return value


class EmailMessageSerializer(serializers.ModelSerializer):
    """Serializer for EmailMessage model"""
    
    account_email = serializers.CharField(source='account.email_address', read_only=True)
    
    class Meta:
        model = EmailMessage
        fields = ('id', 'account', 'account_email', 'message_id', 'subject', 
                 'sender_email', 'sender_name', 'category', 'priority', 
                 'ai_confidence', 'manual_override', 'is_read', 'is_starred', 
                 'is_archived', 'has_attachments', 'has_draft_reply', 
                 'received_at', 'created_at')
        read_only_fields = ('id', 'message_id', 'ai_confidence', 'created_at', 
                           'has_draft_reply', 'account_email')


class EmailMessageDetailSerializer(EmailMessageSerializer):
    """Detailed serializer for EmailMessage with full content"""
    
    class Meta(EmailMessageSerializer.Meta):
        fields = EmailMessageSerializer.Meta.fields + (
            'recipient_emails', 'cc_emails', 'bcc_emails', 
            'body_text', 'body_html', 'draft_reply_content', 'draft_generated_at'
        )


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for UserPreference model"""
    
    class Meta:
        model = UserPreference
        fields = ('default_tone', 'signature', 'auto_categorize', 
                 'auto_generate_drafts', 'category_rules', 'notification_settings',
                 'ai_confidence_threshold', 'learning_enabled', 'updated_at')
        read_only_fields = ('updated_at',)


class MeetingSerializer(serializers.ModelSerializer):
    """Serializer for Meeting model"""
    
    duration_minutes = serializers.ReadOnlyField()
    
    class Meta:
        model = Meeting
        fields = ('id', 'title', 'description', 'platform', 'meeting_url',
                 'scheduled_start', 'scheduled_end', 'actual_start', 'actual_end',
                 'organizer_email', 'participants', 'status', 'has_recording',
                 'has_transcript', 'duration_minutes', 'created_at')
        read_only_fields = ('id', 'duration_minutes', 'created_at')


class MeetingDetailSerializer(MeetingSerializer):
    """Detailed serializer for Meeting with AI content"""
    
    class Meta(MeetingSerializer.Meta):
        fields = MeetingSerializer.Meta.fields + (
            'recording_url', 'transcript_url', 'summary', 'action_items',
            'key_topics', 'follow_up_emails', 'transcription_completed',
            'summary_generated'
        )


class EmailDraftSerializer(serializers.Serializer):
    """Serializer for AI-generated email draft requests"""
    
    message_id = serializers.CharField()
    tone = serializers.ChoiceField(
        choices=UserPreference.TONE_CHOICES,
        default='professional'
    )
    additional_context = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Additional context or instructions for the AI"
    )
    
    def validate_message_id(self, value):
        """Ensure the message exists and belongs to the user"""
        user = self.context['request'].user
        try:
            message = EmailMessage.objects.get(
                message_id=value,
                account__user=user
            )
        except EmailMessage.DoesNotExist:
            raise serializers.ValidationError("Message not found or not accessible.")
        return value


class CategoryUpdateSerializer(serializers.Serializer):
    """Serializer for manual email category updates"""
    
    category = serializers.ChoiceField(choices=EmailMessage.CATEGORY_CHOICES)
    priority = serializers.ChoiceField(
        choices=EmailMessage.PRIORITY_CHOICES, 
        default='medium'
    )
    
    def update(self, instance, validated_data):
        """Update email category and mark as manual override"""
        instance.category = validated_data['category']
        instance.priority = validated_data['priority']
        instance.manual_override = True
        instance.save()
        return instance


class HealthCheckSerializer(serializers.Serializer):
    """Serializer for health check responses"""
    
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    version = serializers.CharField()
    database = serializers.BooleanField()
    redis = serializers.BooleanField(required=False)
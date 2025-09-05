"""
Real-time notification service for email events
"""

import json
from typing import Dict, List, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models import EmailMessage, EmailAccount

User = get_user_model()


class RealTimeNotificationService:
    """
    Service for sending real-time notifications to WebSocket clients
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def notify_new_email(self, email: EmailMessage):
        """
        Send notification for new email received
        
        Args:
            email: EmailMessage instance
        """
        user_id = email.account.user.id
        
        # Prepare notification data
        notification_data = {
            'id': email.id,
            'subject': email.subject,
            'sender': email.sender_email,
            'category': email.category,
            'priority': email.priority,
            'received_at': email.received_at.isoformat(),
            'account_email': email.account.email_address,
            'account_provider': email.account.provider,
            'is_urgent': email.category == 'urgent'
        }
        
        # Send to notifications group
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='notifications',
            message_type='new_email_notification',
            data=notification_data
        )
        
        # If urgent, also send urgent alert
        if email.category == 'urgent':
            self.notify_urgent_email(email)
    
    def notify_urgent_email(self, email: EmailMessage):
        """
        Send urgent email alert
        
        Args:
            email: EmailMessage instance marked as urgent
        """
        user_id = email.account.user.id
        
        alert_data = {
            'id': email.id,
            'subject': email.subject,
            'sender': email.sender,
            'received_at': email.received_at.isoformat(),
            'account_email': email.account.email,
            'message': f'Urgent email from {email.sender}: {email.subject[:50]}...'
        }
        
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='notifications',
            message_type='urgent_email_alert',
            data=alert_data
        )
    
    def notify_email_categorized(self, email: EmailMessage, old_category: str):
        """
        Send notification when email category changes
        
        Args:
            email: EmailMessage instance
            old_category: Previous category
        """
        user_id = email.account.user.id
        
        categorization_data = {
            'id': email.id,
            'subject': email.subject,
            'old_category': old_category,
            'new_category': email.category,
            'confidence_score': email.confidence_score,
            'account_email': email.account.email
        }
        
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='sync',
            message_type='email_categorized',
            data=categorization_data
        )
    
    def notify_sync_progress(self, user_id: int, progress_data: Dict):
        """
        Send sync progress update
        
        Args:
            user_id: User ID
            progress_data: Progress information
        """
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='sync',
            message_type='sync_progress',
            data=progress_data
        )
    
    def notify_sync_completed(self, user_id: int, result_data: Dict):
        """
        Send sync completion notification
        
        Args:
            user_id: User ID
            result_data: Sync results
        """
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='sync',
            message_type='sync_completed',
            data=result_data
        )
    
    def notify_sync_status_update(self, user_id: int, status_data: Dict):
        """
        Send sync status update
        
        Args:
            user_id: User ID
            status_data: Status information
        """
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='notifications',
            message_type='sync_status_update',
            data=status_data
        )
    
    def notify_account_connected(self, account: EmailAccount):
        """
        Send notification when new email account is connected
        
        Args:
            account: EmailAccount instance
        """
        user_id = account.user.id
        
        account_data = {
            'id': account.id,
            'email': account.email_address,
            'provider': account.provider,
            'connected_at': timezone.now().isoformat(),
            'message': f'Successfully connected {account.provider} account: {account.email_address}'
        }
        
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='notifications',
            message_type='account_connected',
            data=account_data
        )
    
    def notify_account_error(self, user_id: int, account_email: str, error_message: str):
        """
        Send notification for account connection errors
        
        Args:
            user_id: User ID
            account_email: Email account that failed
            error_message: Error description
        """
        error_data = {
            'account_email': account_email,
            'error_message': error_message,
            'timestamp': timezone.now().isoformat(),
            'severity': 'error'
        }
        
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='notifications',
            message_type='account_error',
            data=error_data
        )
    
    def notify_bulk_categorization_complete(self, user_id: int, stats: Dict):
        """
        Send notification when bulk categorization is complete
        
        Args:
            user_id: User ID
            stats: Categorization statistics
        """
        self._send_to_user_group(
            user_id=user_id,
            group_suffix='sync',
            message_type='bulk_categorization_complete',
            data=stats
        )
    
    def _send_to_user_group(self, user_id: int, group_suffix: str, message_type: str, data: Dict):
        """
        Send message to user's specific group
        
        Args:
            user_id: User ID
            group_suffix: Group suffix ('sync' or 'notifications')
            message_type: Type of message
            data: Message data
        """
        if not self.channel_layer:
            return
        
        group_name = f"email_{group_suffix}_{user_id}"
        
        try:
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    'type': message_type,
                    'data': data
                }
            )
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Error sending WebSocket notification: {e}")


class NotificationPreferencesService:
    """
    Service for managing user notification preferences
    """
    
    @staticmethod
    def get_user_preferences(user: User) -> Dict:
        """
        Get user notification preferences
        
        Args:
            user: User instance
            
        Returns:
            Dictionary of preferences
        """
        try:
            prefs = user.preferences
            notification_settings = prefs.notification_settings if prefs.notification_settings else {}
        except AttributeError:
            notification_settings = {}
        
        # Default preferences
        defaults = {
            'email_notifications': True,
            'urgent_alerts': True,
            'sync_notifications': True,
            'categorization_updates': False,
            'sound_alerts': True,
            'desktop_notifications': True,
            'quiet_hours': {
                'enabled': False,
                'start_time': '22:00',
                'end_time': '08:00'
            },
            'categories': {
                'urgent': {'enabled': True, 'sound': True},
                'important': {'enabled': True, 'sound': False},
                'routine': {'enabled': False, 'sound': False},
                'promotional': {'enabled': False, 'sound': False},
                'spam': {'enabled': False, 'sound': False}
            }
        }
        
        # Merge with user settings
        for key, default_value in defaults.items():
            if key not in notification_settings:
                notification_settings[key] = default_value
        
        return notification_settings
    
    @staticmethod
    def update_user_preferences(user: User, preferences: Dict) -> bool:
        """
        Update user notification preferences
        
        Args:
            user: User instance
            preferences: New preferences
            
        Returns:
            True if successful
        """
        try:
            if not hasattr(user, 'preferences') or not user.preferences:
                # Create preferences if they don't exist
                from ..models import UserPreference
                prefs = UserPreference.objects.create(user=user)
            else:
                prefs = user.preferences
            
            # Update notification settings
            current_settings = prefs.notification_settings or {}
            current_settings.update(preferences)
            prefs.notification_settings = current_settings
            prefs.save()
            
            return True
            
        except Exception as e:
            print(f"Error updating notification preferences: {e}")
            return False
    
    @staticmethod
    def should_notify_user(user: User, notification_type: str, category: str = None) -> bool:
        """
        Check if user should receive notification based on preferences
        
        Args:
            user: User instance
            notification_type: Type of notification
            category: Email category (if applicable)
            
        Returns:
            True if user should be notified
        """
        prefs = NotificationPreferencesService.get_user_preferences(user)
        
        # Check global settings
        if notification_type == 'email' and not prefs.get('email_notifications', True):
            return False
        
        if notification_type == 'urgent' and not prefs.get('urgent_alerts', True):
            return False
        
        if notification_type == 'sync' and not prefs.get('sync_notifications', True):
            return False
        
        # Check category-specific settings
        if category:
            category_prefs = prefs.get('categories', {}).get(category, {})
            if not category_prefs.get('enabled', True):
                return False
        
        # Check quiet hours
        quiet_hours = prefs.get('quiet_hours', {})
        if quiet_hours.get('enabled', False):
            current_time = timezone.now().time()
            start_time = timezone.datetime.strptime(
                quiet_hours.get('start_time', '22:00'), '%H:%M'
            ).time()
            end_time = timezone.datetime.strptime(
                quiet_hours.get('end_time', '08:00'), '%H:%M'
            ).time()
            
            if start_time <= current_time or current_time <= end_time:
                # In quiet hours, only allow urgent notifications
                if notification_type != 'urgent':
                    return False
        
        return True


# Global instance for easy access
notification_service = RealTimeNotificationService()
preferences_service = NotificationPreferencesService()

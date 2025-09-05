"""
WebSocket consumers for real-time email sync and notifications
"""

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import EmailAccount, EmailMessage
from .services.account_sync import CrossAccountSyncManager
from .tasks import sync_user_accounts

User = get_user_model()


class EmailSyncConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time email synchronization updates
    """
    
    async def connect(self):
        """Accept WebSocket connection and join user's sync group"""
        self.user = self.scope.get("user")

        # Accept early so handshake doesn't fail on backend errors
        await self.accept()

        if not self.user or self.user.is_anonymous:
            await self.send_error("Authentication required for real-time sync")
            await self.close()
            return

        # Create unique group name for this user
        self.group_name = f"email_sync_{self.user.id}"

        # Join the user's sync group (tolerate channel layer issues)
        try:
            if self.channel_layer:
                await self.channel_layer.group_add(
                    self.group_name,
                    self.channel_name
                )
        except Exception as e:
            await self.send_error(f"Realtime backend unavailable: {str(e)}")
            # Keep connection open; client can retry later
            return

        # Send initial sync status
        await self.send_sync_status()
    
    async def disconnect(self, close_code):
        """Leave the sync group when disconnecting"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'start_sync':
                await self.handle_start_sync(data)
            elif message_type == 'get_status':
                await self.send_sync_status()
            elif message_type == 'subscribe_notifications':
                await self.subscribe_to_notifications()
            elif message_type == 'mark_read':
                await self.handle_mark_read(data)
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(f"Error processing message: {str(e)}")
    
    async def handle_start_sync(self, data):
        """Start email synchronization for user accounts"""
        force_full_sync = data.get('force_full_sync', False)
        
        try:
            # Get user's active accounts
            accounts = await self.get_user_accounts()
            
            if not accounts:
                await self.send_error("No active email accounts found")
                return
            
            # Send sync started notification
            await self.send(text_data=json.dumps({
                'type': 'sync_started',
                'accounts_count': len(accounts),
                'force_full_sync': force_full_sync,
                'timestamp': timezone.now().isoformat()
            }))
            
            # Start background sync task
            task_result = await self.start_sync_task(force_full_sync)
            
            await self.send(text_data=json.dumps({
                'type': 'sync_queued',
                'task_id': task_result.id if task_result else None,
                'timestamp': timezone.now().isoformat()
            }))
            
        except Exception as e:
            await self.send_error(f"Failed to start sync: {str(e)}")
    
    async def send_sync_status(self):
        """Send current sync status to the client"""
        try:
            status = await self.get_sync_status()
            
            await self.send(text_data=json.dumps({
                'type': 'sync_status',
                'data': status,
                'timestamp': timezone.now().isoformat()
            }))
            
        except Exception as e:
            await self.send_error(f"Failed to get sync status: {str(e)}")
    
    async def subscribe_to_notifications(self):
        """Subscribe to email notifications"""
        # Join notifications group
        notifications_group = f"email_notifications_{self.user.id}"
        await self.channel_layer.group_add(
            notifications_group,
            self.channel_name
        )
        
        await self.send(text_data=json.dumps({
            'type': 'notifications_subscribed',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def handle_mark_read(self, data):
        """Mark emails as read"""
        email_ids = data.get('email_ids', [])
        
        if not email_ids:
            await self.send_error("No email IDs provided")
            return
        
        try:
            marked_count = await self.mark_emails_read(email_ids)
            
            await self.send(text_data=json.dumps({
                'type': 'emails_marked_read',
                'count': marked_count,
                'email_ids': email_ids,
                'timestamp': timezone.now().isoformat()
            }))
            
        except Exception as e:
            await self.send_error(f"Failed to mark emails as read: {str(e)}")
    
    # Group message handlers
    async def sync_progress(self, event):
        """Send sync progress update to client"""
        await self.send(text_data=json.dumps({
            'type': 'sync_progress',
            'data': event['data'],
            'timestamp': timezone.now().isoformat()
        }))
    
    async def sync_completed(self, event):
        """Send sync completion notification to client"""
        await self.send(text_data=json.dumps({
            'type': 'sync_completed',
            'data': event['data'],
            'timestamp': timezone.now().isoformat()
        }))
    
    async def new_email_notification(self, event):
        """Send new email notification to client"""
        await self.send(text_data=json.dumps({
            'type': 'new_email',
            'data': event['data'],
            'timestamp': timezone.now().isoformat()
        }))
    
    async def email_categorized(self, event):
        """Send email categorization update to client"""
        await self.send(text_data=json.dumps({
            'type': 'email_categorized',
            'data': event['data'],
            'timestamp': timezone.now().isoformat()
        }))
    
    # Database operations
    @database_sync_to_async
    def get_user_accounts(self):
        """Get user's active email accounts"""
        return list(
            EmailAccount.objects.filter(
                user=self.user,
                is_active=True
            ).values('id', 'email_address', 'provider')
        )
    
    @database_sync_to_async
    def get_sync_status(self):
        """Get current sync status for user"""
        sync_manager = CrossAccountSyncManager(self.user)
        status = sync_manager.get_sync_status()
        
        # Add recent email stats
        recent_date = timezone.now() - timedelta(hours=1)
        recent_emails = EmailMessage.objects.filter(
            account__user=self.user,
            received_at__gte=recent_date
        ).count()
        
        status['recent_emails_count'] = recent_emails
        status['last_updated'] = timezone.now().isoformat()
        
        return status
    
    @database_sync_to_async
    def start_sync_task(self, force_full_sync):
        """Start background sync task"""
        return sync_user_accounts.delay(self.user.id, force_full_sync)
    
    @database_sync_to_async
    def mark_emails_read(self, email_ids):
        """Mark emails as read in database"""
        updated = EmailMessage.objects.filter(
            id__in=email_ids,
            account__user=self.user
        ).update(is_read=True)
        
        return updated
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat()
        }))


class EmailNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time email notifications
    """
    
    async def connect(self):
        """Accept connection and join notifications group"""
        self.user = self.scope.get("user")

        # Accept early so handshake succeeds
        await self.accept()

        if not self.user or self.user.is_anonymous:
            await self.send_error("Authentication required for notifications")
            await self.close()
            return

        self.group_name = f"email_notifications_{self.user.id}"

        try:
            if self.channel_layer:
                await self.channel_layer.group_add(
                    self.group_name,
                    self.channel_name
                )
        except Exception as e:
            await self.send_error(f"Realtime backend unavailable: {str(e)}")
            return

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Real-time notifications enabled',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def disconnect(self, close_code):
        """Leave notifications group"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming notification preferences"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'update_preferences':
                await self.handle_notification_preferences(data)
            elif message_type == 'get_unread_count':
                await self.send_unread_count()
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(f"Error: {str(e)}")
    
    async def handle_notification_preferences(self, data):
        """Update user notification preferences"""
        preferences = data.get('preferences', {})
        
        # Save preferences (simplified version)
        await self.send(text_data=json.dumps({
            'type': 'preferences_updated',
            'preferences': preferences,
            'timestamp': timezone.now().isoformat()
        }))
    
    async def send_unread_count(self):
        """Send current unread email count"""
        try:
            unread_count = await self.get_unread_count()
            
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': unread_count,
                'timestamp': timezone.now().isoformat()
            }))
            
        except Exception as e:
            await self.send_error(f"Failed to get unread count: {str(e)}")
    
    # Group message handlers
    async def urgent_email_alert(self, event):
        """Send urgent email alert to client"""
        await self.send(text_data=json.dumps({
            'type': 'urgent_alert',
            'data': event['data'],
            'timestamp': timezone.now().isoformat()
        }))
    
    async def new_email_notification(self, event):
        """Send new email notification"""
        await self.send(text_data=json.dumps({
            'type': 'new_email_notification',
            'data': event['data'],
            'timestamp': timezone.now().isoformat()
        }))
    
    async def sync_status_update(self, event):
        """Send sync status update"""
        await self.send(text_data=json.dumps({
            'type': 'sync_status_update',
            'data': event['data'],
            'timestamp': timezone.now().isoformat()
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread email count for user"""
        return EmailMessage.objects.filter(
            account__user=self.user,
            is_read=False
        ).count()
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat()
        }))

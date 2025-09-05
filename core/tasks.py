"""
FYXERAI Celery Tasks for Background Processing
Handles email synchronization, categorization, and learning tasks
"""

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json

from .models import EmailAccount, EmailMessage, UserPreference
from .services.account_sync import CrossAccountSyncManager
from .services.categorization_engine import EmailCategorizationEngine

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def sync_user_accounts(self, user_id: int, force_full_sync: bool = False):
    """
    Background task to synchronize all accounts for a user.
    
    Args:
        user_id: ID of the user whose accounts to sync
        force_full_sync: Whether to perform a full sync
    """
    try:
        user = User.objects.get(id=user_id)
        sync_manager = CrossAccountSyncManager(user)
        
        result = sync_manager.sync_all_accounts(force_full_sync)
        
        # Log the result
        print(f"Sync completed for user {user_id}: {result['accounts_synced']}/{result['total_accounts']} accounts synced")
        
        return {
            'success': True,
            'user_id': user_id,
            'result': result,
            'task_id': self.request.id
        }
        
    except User.DoesNotExist:
        return {
            'success': False,
            'error': f'User {user_id} not found',
            'task_id': self.request.id
        }
    except Exception as exc:
        # Retry on failure
        if self.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.retries + 1), exc=exc)
        
        return {
            'success': False,
            'error': str(exc),
            'user_id': user_id,
            'task_id': self.request.id
        }


@shared_task(bind=True)
def sync_all_users_accounts(self):
    """
    Background task to sync accounts for all active users.
    Should be run periodically (e.g., every hour).
    """
    try:
        # Get all users who have active email accounts
        users_with_accounts = User.objects.filter(
            email_accounts__is_active=True
        ).distinct()
        
        total_users = users_with_accounts.count()
        successful_syncs = 0
        failed_syncs = 0
        
        for user in users_with_accounts:
            try:
                # Queue individual sync tasks
                sync_user_accounts.delay(user.id, force_full_sync=False)
                successful_syncs += 1
                
            except Exception as e:
                failed_syncs += 1
                print(f"Failed to queue sync for user {user.id}: {e}")
        
        return {
            'success': True,
            'total_users': total_users,
            'queued_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'task_id': self.request.id
        }
        
    except Exception as exc:
        return {
            'success': False,
            'error': str(exc),
            'task_id': self.request.id
        }


@shared_task(bind=True)
def recategorize_pending_emails(self, user_id: int = None, days_back: int = 7):
    """
    Background task to recategorize pending emails using updated algorithms.
    
    Args:
        user_id: Optional user ID to limit scope
        days_back: How many days back to process
    """
    try:
        # Build query for pending emails
        recent_date = timezone.now() - timedelta(days=days_back)
        
        query = EmailMessage.objects.filter(
            category='pending',
            received_at__gte=recent_date
        )
        
        if user_id:
            query = query.filter(account__user_id=user_id)
        
        pending_emails = query.select_related('account__user')
        
        processed_count = 0
        updated_count = 0
        user_engines = {}  # Cache engines per user
        
        for email in pending_emails:
            try:
                user = email.account.user
                
                # Get or create engine for this user
                if user.id not in user_engines:
                    user_engines[user.id] = EmailCategorizationEngine(user)
                
                engine = user_engines[user.id]
                
                # Convert email to dict for categorization
                email_data = {
                    'id': email.message_id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'body': email.body_text,
                    'date': email.received_at
                }
                
                # Get new categorization
                result = engine.categorize_email(email_data)

                # Map AI categories to model choices
                category_map = {
                    'urgent': 'urgent',
                    'important': 'important',
                    'routine': 'other',
                    'promotional': 'promotion',
                    'spam': 'spam',
                }
                model_category = category_map.get(result['category'], 'other')

                # Map numeric priority (1-5) to model priority choices
                pr = result.get('priority', 3)
                if pr >= 4:
                    model_priority = 'high'
                elif pr == 3:
                    model_priority = 'medium'
                else:
                    model_priority = 'low'
                
                # Update email if category changed
                if result['category'] != 'pending':
                    email.category = model_category
                    email.priority = model_priority
                    email.ai_confidence = result['confidence']
                    email.save()
                    updated_count += 1
                
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing email {email.id}: {e}")
                continue
        
        return {
            'success': True,
            'processed_emails': processed_count,
            'updated_emails': updated_count,
            'users_processed': len(user_engines),
            'task_id': self.request.id
        }
        
    except Exception as exc:
        return {
            'success': False,
            'error': str(exc),
            'task_id': self.request.id
        }


@shared_task(bind=True)
def update_user_categorization_rules(self, user_id: int):
    """
    Background task to update a user's categorization rules based on recent activity.
    
    Args:
        user_id: ID of the user to update rules for
    """
    try:
        user = User.objects.get(id=user_id)
        engine = EmailCategorizationEngine(user)
        
        # Reload learning data (this will update patterns)
        engine.learning_data = engine._load_learning_data()
        
        # Get updated stats
        stats = engine.get_category_stats()
        
        return {
            'success': True,
            'user_id': user_id,
            'stats': stats,
            'task_id': self.request.id
        }
        
    except User.DoesNotExist:
        return {
            'success': False,
            'error': f'User {user_id} not found',
            'task_id': self.request.id
        }
    except Exception as exc:
        return {
            'success': False,
            'error': str(exc),
            'user_id': user_id,
            'task_id': self.request.id
        }


@shared_task(bind=True)
def cleanup_old_emails(self, days_old: int = 90):
    """
    Background task to clean up very old emails to manage database size.
    
    Args:
        days_old: Delete emails older than this many days
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        # Only delete emails that are not important or urgent
        old_emails = EmailMessage.objects.filter(
            received_at__lt=cutoff_date,
            category__in=['routine', 'promotional', 'spam']
        )
        
        count_before = old_emails.count()
        deleted_count, _ = old_emails.delete()
        
        return {
            'success': True,
            'emails_deleted': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'task_id': self.request.id
        }
        
    except Exception as exc:
        return {
            'success': False,
            'error': str(exc),
            'task_id': self.request.id
        }


@shared_task(bind=True)
def generate_categorization_report(self, user_id: int, days_back: int = 30):
    """
    Background task to generate a detailed categorization report for a user.
    
    Args:
        user_id: ID of the user to generate report for
        days_back: How many days back to analyze
    """
    try:
        user = User.objects.get(id=user_id)
        recent_date = timezone.now() - timedelta(days=days_back)
        
        # Get email statistics
        emails = EmailMessage.objects.filter(
            account__user=user,
            received_at__gte=recent_date
        )
        
        total_emails = emails.count()
        category_counts = {}
        avg_confidence = {}
        
        for category in ['urgent', 'important', 'routine', 'promotional', 'spam', 'pending']:
            category_emails = emails.filter(category=category)
            count = category_emails.count()
            category_counts[category] = count
            
            # Calculate average confidence for this category
            if count > 0:
                confidences = category_emails.exclude(
                    confidence_score__isnull=True
                ).values_list('confidence_score', flat=True)
                if confidences:
                    avg_confidence[category] = round(sum(confidences) / len(confidences), 3)
                else:
                    avg_confidence[category] = 0.0
            else:
                avg_confidence[category] = 0.0
        
        # Generate insights
        insights = []
        
        # Check for high spam volume
        spam_percentage = (category_counts.get('spam', 0) / max(total_emails, 1)) * 100
        if spam_percentage > 20:
            insights.append({
                'type': 'warning',
                'message': f'High spam volume detected: {spam_percentage:.1f}% of emails',
                'recommendation': 'Consider reviewing spam filters or unsubscribing from unwanted lists'
            })
        
        # Check for pending emails
        pending_count = category_counts.get('pending', 0)
        if pending_count > 50:
            insights.append({
                'type': 'info',
                'message': f'{pending_count} emails are still pending categorization',
                'recommendation': 'Run recategorization to process pending emails'
            })
        
        # Check confidence levels
        low_confidence_categories = [
            cat for cat, conf in avg_confidence.items() 
            if conf > 0 and conf < 0.6 and category_counts.get(cat, 0) > 5
        ]
        if low_confidence_categories:
            insights.append({
                'type': 'warning',
                'message': f'Low confidence in categories: {", ".join(low_confidence_categories)}',
                'recommendation': 'Provide feedback on these categories to improve accuracy'
            })
        
        report = {
            'user_id': user_id,
            'period_days': days_back,
            'total_emails': total_emails,
            'category_counts': category_counts,
            'category_percentages': {
                cat: round((count / max(total_emails, 1)) * 100, 1)
                for cat, count in category_counts.items()
            },
            'average_confidence': avg_confidence,
            'insights': insights,
            'generated_at': timezone.now().isoformat()
        }
        
        return {
            'success': True,
            'report': report,
            'task_id': self.request.id
        }
        
    except User.DoesNotExist:
        return {
            'success': False,
            'error': f'User {user_id} not found',
            'task_id': self.request.id
        }
    except Exception as exc:
        return {
            'success': False,
            'error': str(exc),
            'user_id': user_id,
            'task_id': self.request.id
        }

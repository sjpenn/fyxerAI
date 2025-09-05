"""
FYXERAI Cross-Account Email Synchronization Service
Handles synchronization and categorization across multiple email accounts
"""

import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models import EmailAccount, EmailMessage, UserPreference
from .categorization_engine import EmailCategorizationEngine, categorize_emails_batch
from .notification_service import notification_service

User = get_user_model()


class CrossAccountSyncManager:
    """
    Manages email synchronization and categorization across multiple accounts.
    Provides unified categorization rules and learning across all user accounts.
    """
    
    def __init__(self, user: User):
        self.user = user
        self.categorization_engine = EmailCategorizationEngine(user)
        self.sync_status = {}
    
    def sync_all_accounts(self, force_full_sync: bool = False) -> Dict:
        """
        Synchronize emails across all user accounts and apply categorization.
        
        Args:
            force_full_sync: If True, sync all emails regardless of last sync time
            
        Returns:
            Dictionary with sync results and statistics
        """
        accounts = EmailAccount.objects.filter(user=self.user, is_active=True)
        
        if not accounts.exists():
            return {
                'success': False,
                'message': 'No active email accounts found',
                'accounts_synced': 0
            }
        
        # Send initial sync progress
        notification_service.notify_sync_progress(self.user.id, {
            'status': 'starting',
            'total_accounts': len(accounts),
            'completed_accounts': 0,
            'current_account': None
        })
        
        sync_results = []
        total_emails_processed = 0
        completed_accounts = 0
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit sync tasks for each account
            future_to_account = {
                executor.submit(
                    self._sync_account, account, force_full_sync
                ): account for account in accounts
            }
            
            # Collect results
            for future in future_to_account:
                account = future_to_account[future]
                
                # Send progress update
                notification_service.notify_sync_progress(self.user.id, {
                    'status': 'syncing_account',
                    'total_accounts': len(accounts),
                    'completed_accounts': completed_accounts,
                    'current_account': account.email_address
                })
                
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per account
                    result['account_id'] = account.id
                    result['account_email'] = account.email_address
                    sync_results.append(result)
                    total_emails_processed += result.get('emails_processed', 0)
                    completed_accounts += 1
                    
                    # Send account completion update
                    notification_service.notify_sync_progress(self.user.id, {
                        'status': 'account_completed',
                        'total_accounts': len(accounts),
                        'completed_accounts': completed_accounts,
                        'account_email': account.email_address,
                        'emails_processed': result.get('emails_processed', 0)
                    })
                    
                except Exception as e:
                    sync_results.append({
                        'account_id': account.id,
                        'account_email': account.email,
                        'success': False,
                        'error': str(e),
                        'emails_processed': 0
                    })
                    
                    # Send error notification
                    notification_service.notify_account_error(self.user.id, account.email_address, str(e))
        
        # Apply cross-account learning
        if total_emails_processed > 0:
            notification_service.notify_sync_progress(self.user.id, {
                'status': 'applying_learning',
                'total_accounts': len(accounts),
                'completed_accounts': completed_accounts
            })
            self._apply_cross_account_learning()
        
        # Send final completion notification
        final_result = {
            'success': True,
            'accounts_synced': len([r for r in sync_results if r.get('success', False)]),
            'total_accounts': len(accounts),
            'total_emails_processed': total_emails_processed,
            'sync_results': sync_results,
            'sync_timestamp': timezone.now().isoformat()
        }
        
        notification_service.notify_sync_completed(self.user.id, final_result)
        
        return final_result
    
    def _sync_account(self, account: EmailAccount, force_full_sync: bool = False) -> Dict:
        """
        Synchronize emails for a single account.
        
        Args:
            account: EmailAccount instance
            force_full_sync: Whether to perform full sync
            
        Returns:
            Dictionary with sync result for this account
        """
        try:
            # Determine sync window
            if force_full_sync or not account.last_sync:
                sync_since = timezone.now() - timedelta(days=30)  # Last 30 days for full sync
            else:
                sync_since = account.last_sync - timedelta(hours=1)  # 1 hour overlap
            
            # Mock email fetching (in production, this would use Gmail/Outlook APIs)
            new_emails = self._fetch_emails_from_provider(account, sync_since)
            
            emails_processed = 0
            emails_categorized = 0
            
            with transaction.atomic():
                for email_data in new_emails:
                    # Check if email already exists
                    if EmailMessage.objects.filter(
                        account=account,
                        message_id=email_data.get('message_id', email_data.get('id'))
                    ).exists():
                        continue
                    
                    # Categorize the email
                    categorization = self.categorization_engine.categorize_email(email_data)
                    
                    # Create EmailMessage (map provider fields to model)
                    EmailMessage.objects.create(
                        account=account,
                        message_id=email_data.get('message_id', email_data.get('id')),
                        subject=email_data.get('subject', '')[:500],
                        sender_email=(email_data.get('sender_email') or email_data.get('sender', ''))[:255],
                        sender_name=email_data.get('sender_name', '')[:255],
                        recipient_emails=[(email_data.get('recipient') or account.email_address)[:255]],
                        body_text=email_data.get('body', '')[:5000],
                        category=categorization.get('category', 'other'),
                        priority=categorization.get('priority', 'medium'),
                        ai_confidence=categorization.get('confidence', 0.0),
                        received_at=self._parse_email_date(email_data.get('date')),
                        is_read=email_data.get('is_read', False),
                        has_attachments=email_data.get('has_attachments', False)
                    )
                    
                    emails_processed += 1
                    emails_categorized += 1
                
                # Update account sync timestamp
                account.last_sync = timezone.now()
                account.save()
            
            return {
                'success': True,
                'emails_processed': emails_processed,
                'emails_categorized': emails_categorized,
                'sync_window': sync_since.isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'emails_processed': 0
            }
    
    def _fetch_emails_from_provider(self, account: EmailAccount, since: datetime) -> List[Dict]:
        """Fetch emails using provider APIs (Gmail supported)."""
        try:
            if account.provider == 'gmail':
                # Use read-only scope for listing to minimize privileges
                service = get_gmail_service(
                    account.email_address,
                    scopes=['https://www.googleapis.com/auth/gmail.readonly']
                )
                if not service or not service.is_authenticated():
                    return []
                return service.fetch_emails(since_date=since, max_results=100)
            return []
        except Exception as e:
            notification_service.notify_account_error(self.user.id, account.email_address, str(e))
            return []
    
    def _parse_email_date(self, date_string) -> datetime:
        """Parse email date string into datetime object."""
        if isinstance(date_string, datetime):
            return date_string
        
        if isinstance(date_string, str):
            # In production, implement proper email date parsing
            try:
                return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            except:
                pass
        
        # Fallback to current time
        return timezone.now()
    
    def _apply_cross_account_learning(self):
        """
        Apply learning patterns across all user accounts.
        This helps improve categorization by learning from patterns across accounts.
        """
        try:
            # Analyze patterns across all user accounts
            all_emails = EmailMessage.objects.filter(
                account__user=self.user,
                received_at__gte=timezone.now() - timedelta(days=60)
            ).exclude(category='pending')
            
            # Build cross-account sender patterns
            sender_patterns = {}
            for email in all_emails:
                sender_domain = email.sender.split('@')[-1] if '@' in email.sender else email.sender
                
                if sender_domain not in sender_patterns:
                    sender_patterns[sender_domain] = {}
                
                category = email.category
                if category not in sender_patterns[sender_domain]:
                    sender_patterns[sender_domain][category] = 0
                    
                sender_patterns[sender_domain][category] += 1
            
            # Update user preferences with cross-account patterns
            preferences, created = UserPreference.objects.get_or_create(
                user=self.user,
                defaults={'categorization_rules': '{}'}
            )
            
            current_rules = json.loads(preferences.categorization_rules or '{}')
            
            # Merge cross-account learning
            current_rules['cross_account_patterns'] = {
                'sender_domains': sender_patterns,
                'last_updated': timezone.now().isoformat(),
                'total_emails_analyzed': all_emails.count()
            }
            
            preferences.categorization_rules = json.dumps(current_rules)
            preferences.save()
            
        except Exception as e:
            # Log error but don't break the sync process
            print(f"Error applying cross-account learning: {e}")
    
    def get_sync_status(self) -> Dict:
        """Get current synchronization status for all accounts."""
        accounts = EmailAccount.objects.filter(user=self.user)
        
        account_statuses = []
        for account in accounts:
            # Get recent email counts
            recent_count = EmailMessage.objects.filter(
                account=account,
                received_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            account_statuses.append({
                'account_id': account.id,
                'email': account.email_address,
                'provider': account.provider,
                'is_active': account.is_active,
                'last_sync': account.last_sync.isoformat() if account.last_sync else None,
                'recent_emails': recent_count,
                'total_emails': EmailMessage.objects.filter(account=account).count()
            })
        
        return {
            'user_id': self.user.id,
            'total_accounts': len(account_statuses),
            'active_accounts': len([a for a in account_statuses if a['is_active']]),
            'accounts': account_statuses,
            'last_updated': timezone.now().isoformat()
        }
    
    def recategorize_account_emails(self, account_id: int, 
                                  category_filter: Optional[str] = None) -> Dict:
        """
        Recategorize emails for a specific account using updated rules.
        
        Args:
            account_id: ID of the account to recategorize
            category_filter: Optional category to filter (e.g., 'pending')
            
        Returns:
            Dictionary with recategorization results
        """
        try:
            account = EmailAccount.objects.get(id=account_id, user=self.user)
        except EmailAccount.DoesNotExist:
            return {
                'success': False,
                'error': 'Account not found or access denied'
            }
        
        # Build query
        query = Q(account=account)
        if category_filter:
            query &= Q(category=category_filter)
        
        emails = EmailMessage.objects.filter(query)
        
        updated_count = 0
        changed_categories = {}
        
        with transaction.atomic():
            for email in emails:
                # Convert to dict for categorization
                email_data = {
                    'id': email.message_id,
                    'subject': email.subject,
                    'sender': email.sender_email,
                    'body': email.body_text,
                    'date': email.received_at
                }
                
                # Get new categorization
                categorization = self.categorization_engine.categorize_email(email_data)
                
                # Update if category changed
                old_category = email.category
                new_category = categorization['category']
                
                if old_category != new_category:
                    email.category = new_category
                    email.priority = categorization['priority'] 
                    email.ai_confidence = categorization['confidence']
                    email.save()
                    
                    updated_count += 1
                    
                    # Track category changes
                    change_key = f"{old_category} -> {new_category}"
                    changed_categories[change_key] = changed_categories.get(change_key, 0) + 1
        
        return {
            'success': True,
            'account_email': account.email,
            'total_emails_processed': emails.count(),
            'emails_updated': updated_count,
            'category_changes': changed_categories,
            'recategorization_timestamp': timezone.now().isoformat()
        }

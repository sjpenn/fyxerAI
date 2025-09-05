"""
FYXERAI Label Management Service
Coordinates email labeling and actions across Gmail and Outlook platforms
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from django.core.cache import cache
from django.utils import timezone

from .gmail_service import get_gmail_service
from .openai_service import get_openai_service, categorize_with_ai

logger = logging.getLogger(__name__)

class LabelManager:
    """
    Manages label application and email actions based on categorization results.
    Coordinates between different email platforms and applies appropriate actions.
    """
    
    # Action mappings for each category
    CATEGORY_ACTIONS = {
        'urgent': {
            'gmail_actions': ['apply_label', 'mark_important', 'add_star'],
            'outlook_actions': ['apply_category', 'mark_important', 'flag'],
            'notifications': True,
            'priority_level': 5
        },
        'important': {
            'gmail_actions': ['apply_label', 'add_star'],
            'outlook_actions': ['apply_category', 'flag'],
            'notifications': False,
            'priority_level': 4
        },
        'routine': {
            'gmail_actions': ['apply_label'],
            'outlook_actions': ['apply_category'],
            'notifications': False,
            'priority_level': 3
        },
        'promotional': {
            'gmail_actions': ['apply_label', 'move_to_promotions'],
            'outlook_actions': ['apply_category', 'move_to_folder'],
            'notifications': False,
            'priority_level': 2
        },
        'spam': {
            'gmail_actions': ['apply_label', 'move_to_spam'],
            'outlook_actions': ['move_to_junk'],
            'notifications': False,
            'priority_level': 1
        }
    }
    
    def __init__(self, user_email: str, platform: str = 'gmail'):
        self.user_email = user_email
        self.platform = platform.lower()
        self.gmail_service = None
        self.outlook_service = None
        
        # Initialize appropriate service
        if self.platform == 'gmail':
            self.gmail_service = get_gmail_service(user_email)
        elif self.platform == 'outlook':
            # TODO: Initialize Outlook service when implemented
            logger.warning("Outlook service not yet implemented")
    
    def process_triage_results(self, emails: List[Dict], categorization_results: List[Dict], use_batch: bool = True) -> Dict:
        """
        Process categorization results and apply appropriate labels and actions.
        Optionally batch Gmail label application to reduce API calls.
        """
        if len(emails) != len(categorization_results):
            logger.error("Email count mismatch with categorization results")
            return {'success': False, 'error': 'Data mismatch'}
        
        results = {
            'success': True,
            'processed_count': 0,
            'label_applications': [],
            'action_results': [],
            'errors': [],
            'statistics': {
                'urgent': 0,
                'important': 0,
                'routine': 0,
                'promotional': 0,
                'spam': 0
            }
        }
        
        emails_by_category = {}
        
        for email, categorization in zip(emails, categorization_results):
            try:
                email_result = self._process_single_email(email, categorization) if not use_batch else {
                    'email_id': email.get('id'),
                    'category': categorization.get('category', 'routine'),
                    'confidence': categorization.get('confidence', 0.5),
                    'actions_applied': [],
                    'success': True,
                    'error': None
                }
                
                # When batching, collect Gmail apply_label actions; apply others immediately
                category = categorization.get('category', 'routine')
                if use_batch and self.platform == 'gmail':
                    actions_config = self.CATEGORY_ACTIONS.get(category, {})
                    for action in actions_config.get('gmail_actions', []):
                        if action == 'apply_label':
                            emails_by_category.setdefault(category, []).append(email.get('id'))
                            email_result['actions_applied'].append({'action': action, 'success': True, 'timestamp': timezone.now().isoformat()})
                        else:
                            action_result = self._apply_action(email.get('id'), action, category)
                            email_result['actions_applied'].append({'action': action, 'success': action_result, 'timestamp': timezone.now().isoformat()})
                
                if email_result['success']:
                    results['processed_count'] += 1
                    results['label_applications'].append(email_result)
                    results['statistics'][category] += 1
                else:
                    results['errors'].append({'email_id': email.get('id'), 'error': email_result.get('error', 'Unknown error')})
                
            except Exception as e:
                logger.error(f"Failed to process email {email.get('id')}: {e}")
                results['errors'].append({'email_id': email.get('id'), 'error': str(e)})
        
        # Perform batch Gmail label application when requested
        if use_batch and self.platform == 'gmail' and self.gmail_service and emails_by_category:
            try:
                label_ids = self.gmail_service.setup_fyxerai_labels()
                for cat, ids in emails_by_category.items():
                    if ids and cat in label_ids:
                        self.gmail_service.batch_modify(ids, add_label_ids=[label_ids[cat]])
            except Exception as e:
                logger.warning(f"Batch label application failed: {e}")
        
        logger.info(f"Triage processing completed: {results['processed_count']}/{len(emails)} emails processed")
        return results
    
    def _process_single_email(self, email: Dict, categorization: Dict) -> Dict:
        """Process a single email with its categorization result."""
        email_id = email.get('id')
        category = categorization.get('category', 'routine')
        confidence = categorization.get('confidence', 0.5)
        
        logger.info(f"Processing email {email_id} as {category} (confidence: {confidence:.2f})")
        
        result = {
            'email_id': email_id,
            'category': category,
            'confidence': confidence,
            'actions_applied': [],
            'success': True,
            'error': None
        }
        
        try:
            # Get actions for this category and platform
            actions_config = self.CATEGORY_ACTIONS.get(category, {})
            platform_actions = actions_config.get(f'{self.platform}_actions', [])
            
            # Apply each action
            for action in platform_actions:
                action_result = self._apply_action(email_id, action, category)
                result['actions_applied'].append({
                    'action': action,
                    'success': action_result,
                    'timestamp': timezone.now().isoformat()
                })
                
                if not action_result:
                    logger.warning(f"Action {action} failed for email {email_id}")
            
            # Send notifications if required
            if actions_config.get('notifications', False) and confidence > 0.7:
                self._send_notification(email, categorization)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process email {email_id}: {e}")
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def _apply_action(self, email_id: str, action: str, category: str) -> bool:
        """Apply a specific action to an email."""
        try:
            if self.platform == 'gmail' and self.gmail_service:
                return self._apply_gmail_action(email_id, action, category)
            elif self.platform == 'outlook' and self.outlook_service:
                return self._apply_outlook_action(email_id, action, category)
            else:
                logger.warning(f"No service available for platform {self.platform}")
                return False
                
        except Exception as e:
            logger.error(f"Action {action} failed for {email_id}: {e}")
            return False
    
    def _apply_gmail_action(self, email_id: str, action: str, category: str) -> bool:
        """Apply Gmail-specific actions."""
        if not self.gmail_service or not self.gmail_service.is_authenticated():
            logger.warning("Gmail service not available")
            return False
        
        try:
            if action == 'apply_label':
                return self.gmail_service.apply_label(email_id, category)
            
            elif action == 'mark_important':
                return self.gmail_service.mark_important(email_id)
            
            elif action == 'add_star':
                # Use Gmail's STARRED label with retry
                req = self.gmail_service.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'addLabelIds': ['STARRED']}
                )
                return self.gmail_service._execute_with_retry(req) is not None
            
            elif action == 'move_to_promotions':
                # Move to Promotions tab (remove from Inbox, add to CATEGORY_PROMOTIONS) with retry
                req = self.gmail_service.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={
                        'removeLabelIds': ['INBOX'],
                        'addLabelIds': ['CATEGORY_PROMOTIONS']
                    }
                )
                return self.gmail_service._execute_with_retry(req) is not None
            
            elif action == 'move_to_spam':
                return self.gmail_service.move_to_spam(email_id)
            
            else:
                logger.warning(f"Unknown Gmail action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Gmail action {action} failed: {e}")
            return False
    
    def _apply_outlook_action(self, email_id: str, action: str, category: str) -> bool:
        """Apply Outlook-specific actions (placeholder for future implementation)."""
        # TODO: Implement Outlook actions when Outlook service is ready
        logger.info(f"Outlook action {action} for {email_id} (not yet implemented)")
        return True  # Return True for testing purposes
    
    def _send_notification(self, email: Dict, categorization: Dict):
        """Send notification for high-priority emails."""
        try:
            # TODO: Implement notification service
            logger.info(f"Notification triggered for urgent email: {email.get('subject', 'No Subject')}")
            
            # Could integrate with:
            # - Push notifications
            # - Slack/Teams webhooks
            # - SMS alerts
            # - Email notifications
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def setup_labels(self) -> Dict:
        """Initialize labels/categories for the email platform."""
        if self.platform == 'gmail' and self.gmail_service:
            try:
                label_ids = self.gmail_service.setup_fyxerai_labels()
                logger.info(f"Gmail labels setup complete: {list(label_ids.keys())}")
                return {'success': True, 'labels': label_ids}
            except Exception as e:
                logger.error(f"Failed to setup Gmail labels: {e}")
                return {'success': False, 'error': str(e)}
        
        elif self.platform == 'outlook':
            # TODO: Implement Outlook category setup
            logger.info("Outlook category setup (not yet implemented)")
            return {'success': True, 'labels': {}}
        
        else:
            return {'success': False, 'error': f'Unsupported platform: {self.platform}'}
    
    def get_triage_statistics(self, days: int = 7) -> Dict:
        """Get email triage statistics for the past N days."""
        # TODO: Query database for actual statistics
        # For now, return placeholder data
        return {
            'total_emails_triaged': 0,
            'categories': {
                'urgent': 0,
                'important': 0,
                'routine': 0,
                'promotional': 0,
                'spam': 0
            },
            'accuracy_feedback': {
                'correct_classifications': 0,
                'user_corrections': 0,
                'accuracy_rate': 0.0
            },
            'time_saved_minutes': 0,
            'period_days': days
        }
    
    def undo_categorization(self, email_id: str) -> bool:
        """Undo categorization for an email (remove FYXERAI labels)."""
        if self.platform == 'gmail' and self.gmail_service:
            try:
                # Get all FYXERAI labels
                cache_key = f"gmail_labels_{self.user_email}"
                label_ids = cache.get(cache_key)
                
                if not label_ids:
                    label_ids = self.gmail_service.setup_fyxerai_labels()
                    cache.set(cache_key, label_ids, 3600)
                
                # Remove all FYXERAI labels from the email
                req = self.gmail_service.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'removeLabelIds': list(label_ids.values())}
                )
                self.gmail_service._execute_with_retry(req)
                
                logger.info(f"Removed FYXERAI labels from email {email_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to undo categorization for {email_id}: {e}")
                return False
        
        return False


def process_email_triage(user_email: str, emails: List[Dict], platform: str = 'gmail') -> Dict:
    """
    Main function to process email triage with AI categorization and label application.
    
    Args:
        user_email: User's email address
        emails: List of email data from extension
        platform: Email platform (gmail or outlook)
        
    Returns:
        Complete triage results with applied labels and actions
    """
    logger.info(f"Starting email triage for {len(emails)} emails on {platform}")
    
    try:
        # Initialize services
        label_manager = LabelManager(user_email, platform)
        ai_service = get_openai_service()
        
        # Setup labels if needed
        setup_result = label_manager.setup_labels()
        if not setup_result['success']:
            logger.warning(f"Label setup failed: {setup_result.get('error')}")
        
        # Categorize emails using AI
        categorization_results = ai_service.categorize_emails_batch(emails)
        
        # Apply labels and actions
        processing_results = label_manager.process_triage_results(emails, categorization_results)
        
        # Combine results
        final_results = {
            'success': processing_results['success'],
            'processed': processing_results['processed_count'],
            'total_emails': len(emails),
            'categories': categorization_results,
            'label_applications': processing_results['label_applications'],
            'statistics': processing_results['statistics'],
            'errors': processing_results['errors'],
            'platform': platform,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Triage completed: {final_results['processed']}/{len(emails)} emails processed")
        return final_results
        
    except Exception as e:
        logger.error(f"Email triage failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'processed': 0,
            'total_emails': len(emails),
            'platform': platform
        }

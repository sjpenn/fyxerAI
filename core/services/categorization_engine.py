"""
FYXERAI Email Categorization Engine
Intelligent cross-account email classification system with machine learning
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models import EmailMessage, EmailAccount, UserPreference

User = get_user_model()

# Import notification service for real-time updates
# from .notification_service import notification_service  # TODO: Implement later


class EmailCategorizationEngine:
    """
    Advanced email categorization system that learns from user patterns
    across multiple accounts and provides intelligent classification.
    """
    
    # Enhanced category definitions with priorities
    CATEGORIES = {
        'urgent': {
            'priority': 5,
            'description': 'Requires immediate attention within 1-2 hours',
            'keywords': [
                'urgent', 'asap', 'emergency', 'critical', 'deadline today',
                'immediate', 'now', 'rushing', 'crisis', 'breaking'
            ],
            'sender_patterns': [
                'ceo', 'president', 'director', 'manager', 'boss', 'supervisor',
                'legal', 'compliance', 'security', 'incident'
            ],
            'subject_patterns': [
                r'\b(urgent|emergency|critical|asap)\b',
                r'\b(deadline|due)\s+(today|now|immediately)\b',
                r'\b(action required|immediate attention)\b'
            ]
        },
        'important': {
            'priority': 4,
            'description': 'Needs attention within 24 hours',
            'keywords': [
                'meeting', 'project', 'report', 'review', 'approval', 'decision',
                'conference', 'presentation', 'proposal', 'contract', 'budget'
            ],
            'sender_patterns': [
                'client', 'customer', 'partner', 'vendor', 'team lead',
                'project manager', 'account manager', 'stakeholder'
            ],
            'subject_patterns': [
                r'\b(meeting|conference|call)\b',
                r'\b(project|proposal|contract)\b',
                r'\b(review|approval|decision)\b',
                r'\b(report|update|status)\b'
            ]
        },
        'routine': {
            'priority': 3,
            'description': 'Standard business communication',
            'keywords': [
                'update', 'information', 'notification', 'reminder', 'follow-up',
                'schedule', 'confirmation', 'receipt', 'invoice', 'newsletter',
                'digest'
            ],
            'sender_patterns': [
                'team', 'colleague', 'department', 'hr', 'admin',
                'support', 'service', 'billing'
            ],
            'subject_patterns': [
                r'\b(update|information|notification)\b',
                r'\b(reminder|follow.?up|confirmation)\b',
                r'\b(newsletter|digest|summary)\b'
            ]
        },
        'promotional': {
            'priority': 2,
            'description': 'Marketing and promotional content',
            'keywords': [
                'sale', 'discount', 'offer', 'deal', 'promotion', 'special',
                'limited time', 'exclusive', 'save', 'free', 'coupon'
            ],
            'sender_patterns': [
                'marketing', 'sales', 'promo', 'deals', 'offers',
                'newsletter', 'no-reply', 'noreply'
            ],
            'subject_patterns': [
                r'\b(sale|discount|offer|deal)\b',
                r'\b(special|exclusive|limited)\b',
                r'\b(save|free|coupon)\b',
                r'%\s*off\b'
            ]
        },
        'spam': {
            'priority': 1,
            'description': 'Unwanted or suspicious emails',
            'keywords': [
                'winner', 'lottery', 'prize', 'congratulations', 'claim now',
                'inheritance', 'millions', 'prince', 'deceased', 'beneficiary',
                'viagra', 'pills', 'weight loss', 'bitcoin', 'investment'
            ],
            'sender_patterns': [
                'lottery', 'winner', 'claim', 'inheritance', 'beneficiary',
                'investment', 'trading', 'forex'
            ],
            'subject_patterns': [
                r'\b(winner|lottery|prize|congratulations)\b',
                r'\b(claim|inheritance|millions)\b',
                r'\b(viagra|pills|weight.?loss)\b',
                r'\$\d+[,.]?\d*\s*(million|thousand)'
            ]
        },
        'other': {
            'priority': 2,
            'description': 'General or unclassified emails',
            'keywords': [],
            'sender_patterns': [],
            'subject_patterns': []
        }
    }
    
    def __init__(self, user: Optional[User] = None):
        self.user = user
        self.user_preferences = self._load_user_preferences()
        self.learning_data = self._load_learning_data()
    
    def categorize_email(self, email_data: Dict) -> Dict:
        """
        Categorize an email using multiple algorithms and user learning data.
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            Dictionary with category, confidence, and explanation
        """
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('sender', '').lower()
        body = email_data.get('body', '').lower()
        
        # Calculate scores for each category
        category_scores = {}
        
        for category, config in self.CATEGORIES.items():
            score = self._calculate_category_score(
                category, config, subject, sender, body, email_data
            )
            category_scores[category] = score
        
        # Apply user learning data
        if self.learning_data:
            category_scores = self._apply_user_learning(
                category_scores, subject, sender, email_data
            )
        
        # Determine best category
        best_category = max(category_scores.items(), key=lambda x: x[1])
        category_name, confidence = best_category
        
        # Ensure minimum confidence threshold
        # Lowered threshold to avoid over-classifying emails as 'other'
        # when there is a weak but relevant signal (e.g., newsletter digests).
        if confidence < 0.05:
            category_name = 'other'  # Default fallback
            confidence = 0.3
        
        return {
            'category': category_name,
            'confidence': round(confidence, 3),
            'priority': self.CATEGORIES[category_name]['priority'],
            'explanation': self._generate_explanation(
                category_name, confidence, subject, sender
            ),
            'all_scores': {k: round(v, 3) for k, v in category_scores.items()}
        }
    
    def _calculate_category_score(self, category: str, config: Dict, 
                                subject: str, sender: str, body: str, 
                                email_data: Dict) -> float:
        """Calculate relevance score for a specific category."""
        score = 0.0
        
        # Keyword matching in subject (weight: 0.4)
        keyword_score = self._calculate_keyword_score(
            config['keywords'], subject + ' ' + body
        )
        score += keyword_score * 0.4
        
        # Sender pattern matching (weight: 0.3)
        sender_score = self._calculate_sender_score(
            config['sender_patterns'], sender
        )
        score += sender_score * 0.3
        
        # Regex pattern matching (weight: 0.2)
        pattern_score = self._calculate_pattern_score(
            config['subject_patterns'], subject
        )
        score += pattern_score * 0.2
        
        # Time-based scoring (weight: 0.1)
        time_score = self._calculate_time_score(category, email_data)
        score += time_score * 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_keyword_score(self, keywords: List[str], text: str) -> float:
        """Calculate score based on keyword presence."""
        if not text:
            return 0.0
            
        matches = 0
        for keyword in keywords:
            if keyword.lower() in text:
                matches += 1
        
        return min(matches / max(len(keywords) * 0.3, 1), 1.0)
    
    def _calculate_sender_score(self, patterns: List[str], sender: str) -> float:
        """Calculate score based on sender patterns."""
        if not sender:
            return 0.0
            
        matches = 0
        for pattern in patterns:
            if pattern.lower() in sender:
                matches += 1
        
        return min(matches / max(len(patterns) * 0.5, 1), 1.0)
    
    def _calculate_pattern_score(self, patterns: List[str], subject: str) -> float:
        """Calculate score based on regex patterns."""
        if not subject or not patterns:
            return 0.0
            
        matches = 0
        for pattern in patterns:
            if re.search(pattern, subject, re.IGNORECASE):
                matches += 1
        
        return min(matches / len(patterns), 1.0)
    
    def _calculate_time_score(self, category: str, email_data: Dict) -> float:
        """Calculate score based on timing patterns."""
        # This could be enhanced with user's timezone and working hours
        current_hour = datetime.now().hour
        
        # Business hours boost for urgent/important
        if category in ['urgent', 'important'] and 9 <= current_hour <= 17:
            return 0.2
        
        # Evening/weekend boost for spam detection
        if category == 'spam' and (current_hour < 8 or current_hour > 20):
            return 0.1
        
        return 0.0
    
    def _apply_user_learning(self, scores: Dict[str, float], 
                           subject: str, sender: str, 
                           email_data: Dict) -> Dict[str, float]:
        """Apply user learning data to adjust scores."""
        if not self.user or not self.learning_data:
            return scores
        
        # Apply sender-based learning
        sender_adjustments = self.learning_data.get('sender_patterns', {})
        for sender_pattern, category_adjustments in sender_adjustments.items():
            if sender_pattern.lower() in sender:
                for category, adjustment in category_adjustments.items():
                    if category in scores:
                        scores[category] = min(scores[category] + adjustment, 1.0)
        
        # Apply keyword-based learning
        keyword_adjustments = self.learning_data.get('keyword_patterns', {})
        text = (subject + ' ' + email_data.get('body', '')).lower()
        for keyword, category_adjustments in keyword_adjustments.items():
            if keyword.lower() in text:
                for category, adjustment in category_adjustments.items():
                    if category in scores:
                        scores[category] = min(scores[category] + adjustment, 1.0)
        
        return scores
    
    def _load_user_preferences(self) -> Dict:
        """Load user-specific categorization preferences."""
        if not self.user:
            return {}
        
        try:
            preferences = UserPreference.objects.get(user=self.user)
            # Use category_rules field from our actual model
            return preferences.category_rules or {}
        except UserPreference.DoesNotExist:
            return {}
        except (json.JSONDecodeError, AttributeError):
            return {}
    
    def _load_learning_data(self) -> Dict:
        """Load historical learning data for the user."""
        if not self.user:
            return {}
        
        # Analyze user's historical email patterns
        recent_emails = EmailMessage.objects.filter(
            account__user=self.user,
            received_at__gte=timezone.now() - timedelta(days=90)
        ).exclude(category='other')
        
        # Build sender patterns
        sender_patterns = {}
        for email in recent_emails:
            sender_domain = email.sender_email.split('@')[-1] if '@' in email.sender_email else email.sender_email
            if sender_domain not in sender_patterns:
                sender_patterns[sender_domain] = {}
            
            category = email.category
            if category not in sender_patterns[sender_domain]:
                sender_patterns[sender_domain][category] = 0
            sender_patterns[sender_domain][category] += 1
        
        # Convert counts to adjustment scores
        for sender, categories in sender_patterns.items():
            total = sum(categories.values())
            for category, count in categories.items():
                # Higher frequency = positive adjustment (up to 0.2)
                sender_patterns[sender][category] = min((count / total) * 0.2, 0.2)
        
        return {
            'sender_patterns': sender_patterns,
            'keyword_patterns': {},  # Could be enhanced
            'last_updated': timezone.now().isoformat()
        }
    
    def _generate_explanation(self, category: str, confidence: float, 
                            subject: str, sender: str) -> str:
        """Generate human-readable explanation for categorization."""
        config = self.CATEGORIES[category]
        
        explanation_parts = [
            f"Categorized as '{category}' with {confidence:.1%} confidence."
        ]
        
        # Add category description
        explanation_parts.append(config['description'])
        
        # Add reasoning based on matches
        if any(keyword in subject.lower() for keyword in config['keywords'][:3]):
            explanation_parts.append("Subject contains relevant keywords.")
        
        if any(pattern in sender.lower() for pattern in config['sender_patterns'][:2]):
            explanation_parts.append("Sender matches typical pattern for this category.")
        
        return ' '.join(explanation_parts)
    
    def learn_from_user_action(self, email_data: Dict, user_category: str):
        """Learn from user manual categorization to improve future predictions."""
        if not self.user:
            return
        
        # Store learning data in user preferences
        try:
            preferences, created = UserPreference.objects.get_or_create(
                user=self.user,
                defaults={'category_rules': {}}
            )
            
            learning_data = preferences.category_rules or {}
            
            # Update sender learning
            sender = email_data.get('sender', '')
            if sender and '@' in sender:
                sender_domain = sender.split('@')[-1]
                if 'sender_learning' not in learning_data:
                    learning_data['sender_learning'] = {}
                
                if sender_domain not in learning_data['sender_learning']:
                    learning_data['sender_learning'][sender_domain] = {}
                
                if user_category not in learning_data['sender_learning'][sender_domain]:
                    learning_data['sender_learning'][sender_domain][user_category] = 0
                
                learning_data['sender_learning'][sender_domain][user_category] += 1
            
            # Save updated learning data
            preferences.category_rules = learning_data
            preferences.save()
            
        except Exception as e:
            # Log error but don't break the flow
            print(f"Error learning from user action: {e}")
    
    def get_category_stats(self) -> Dict:
        """Get categorization statistics for the user."""
        if not self.user:
            return {}
        
        # Get email counts by category for the last 30 days
        recent_date = timezone.now() - timedelta(days=30)
        
        stats = EmailMessage.objects.filter(
            account__user=self.user,
            received_at__gte=recent_date
        ).values('category').annotate(
            count=Count('id')
        ).order_by('category')
        
        category_counts = {stat['category']: stat['count'] for stat in stats}
        total_emails = sum(category_counts.values())
        
        return {
            'total_emails': total_emails,
            'category_counts': category_counts,
            'category_percentages': {
                category: round((count / total_emails) * 100, 1) if total_emails > 0 else 0
                for category, count in category_counts.items()
            },
            'period': '30 days'
        }
    
    def categorize_and_update_email(self, email: EmailMessage, send_notification: bool = True) -> Dict:
        """
        Categorize an email and update the database with real-time notifications.
        
        Args:
            email: EmailMessage instance to categorize
            send_notification: Whether to send real-time notifications
            
        Returns:
            Categorization result dictionary
        """
        # Store old category for notification
        old_category = email.category
        
        # Prepare email data for categorization
        email_data = {
            'id': email.message_id,
            'subject': email.subject,
            'sender': email.sender_email,
            'body': email.body_text,
            'date': email.received_at,
            'recipient': email.recipient_emails
        }
        
        # Get categorization result
        result = self.categorize_email(email_data)

        # Map AI categories to model choices
        category_map = {
            'urgent': 'urgent',
            'important': 'important',
            'routine': 'other',
            'promotional': 'promotion',
            'spam': 'spam',
        }
        model_category = category_map.get(result['category'], 'other')
        
        # Update email in database
        email.category = model_category
        email.ai_confidence = result['confidence']
        # Note: priority field may need to be added to model or mapped differently
        email.save()
        
        # Send real-time notifications if requested
        if send_notification:
            # Check if this is a new email or recategorization
            if old_category == 'other':
                # New email notification
                pass  # notification_service.notify_new_email(email)
            elif old_category != result['category']:
                # Category changed notification
                pass  # notification_service.notify_email_categorized(email, old_category)
        
        return result
    
    def bulk_categorize_pending_emails(self, limit: int = 50, send_notifications: bool = True) -> Dict:
        """
        Bulk categorize pending emails for the user.
        
        Args:
            limit: Maximum number of emails to process
            send_notifications: Whether to send real-time updates
            
        Returns:
            Statistics about the categorization process
        """
        # Get pending emails for this user (using 'other' as default category)
        pending_emails = EmailMessage.objects.filter(
            account__user=self.user,
            category='other'
        ).order_by('-received_at')[:limit]
        
        if not pending_emails:
            return {
                'processed': 0,
                'updated': 0,
                'categories': {},
                'message': 'No pending emails found'
            }
        
        processed_count = 0
        updated_count = 0
        category_counts = {}
        
        for email in pending_emails:
            try:
                result = self.categorize_and_update_email(email, send_notifications)
                processed_count += 1
                
                if result['category'] != 'other':
                    updated_count += 1
                    category = result['category']
                    category_counts[category] = category_counts.get(category, 0) + 1
                
            except Exception as e:
                print(f"Error categorizing email {email.id}: {e}")
                continue
        
        # Send bulk completion notification
        if send_notifications and updated_count > 0:
            pass  # notification_service.notify_bulk_categorization_complete(...)
        
        return {
            'processed': processed_count,
            'updated': updated_count,
            'categories': category_counts,
            'message': f'Processed {processed_count} emails, updated {updated_count}'
        }


def categorize_emails_batch(emails: List[Dict], user: Optional[User] = None) -> List[Dict]:
    """
    Batch categorize multiple emails efficiently.
    
    Args:
        emails: List of email dictionaries
        user: Optional user for personalized categorization
        
    Returns:
        List of categorization results
    """
    engine = EmailCategorizationEngine(user)
    
    results = []
    for email_data in emails:
        result = engine.categorize_email(email_data)
        result['email_id'] = email_data.get('id')
        results.append(result)
    
    return results

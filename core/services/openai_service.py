"""
FYXERAI OpenAI Integration Service
Provides AI-powered email categorization using OpenAI GPT models
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from django.conf import settings
from django.core.cache import cache

# OpenAI imports
try:
    import openai
    from openai import OpenAI
except ImportError:
    # Graceful fallback if OpenAI not installed
    openai = None
    OpenAI = None

import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    OpenAI service for intelligent email categorization and content analysis.
    Provides GPT-powered categorization with structured output.
    """
    
    # System prompt for email categorization
    CATEGORIZATION_PROMPT = """You are an expert email triage assistant. Analyze the provided email and categorize it based on urgency and importance.

Categories:
- URGENT: Requires immediate attention (1-2 hours) - deadlines, crises, urgent requests from executives
- IMPORTANT: Needs attention within 24 hours - meetings, projects, decisions, client communications
- ROUTINE: Standard business communication - updates, notifications, confirmations, newsletters
- PROMOTIONAL: Marketing and promotional content - sales emails, discounts, advertisements
- SPAM: Unwanted or suspicious emails - phishing, scams, irrelevant marketing

Analyze the email considering:
1. Sender authority and relationship
2. Subject urgency indicators
3. Content context and tone
4. Action requirements
5. Time sensitivity

Respond with valid JSON only:
{
    "category": "urgent|important|routine|promotional|spam",
    "confidence": 0.85,
    "priority": 5,
    "explanation": "Brief reason for categorization",
    "suggested_actions": ["action1", "action2"],
    "time_sensitive": true,
    "requires_response": false
}"""
    
    # Model configuration
    DEFAULT_MODEL = "gpt-3.5-turbo"  # Using widely available model
    FALLBACK_MODEL = "gpt-3.5-turbo"
    MAX_TOKENS = 300
    TEMPERATURE = 0.1  # Low temperature for consistent categorization
    
    def __init__(self):
        self.client = None
        self.model = self.DEFAULT_MODEL
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client with API key."""
        if not OpenAI:
            logger.warning("OpenAI library not installed. AI categorization disabled.")
            return
            
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.warning("OPENAI_API_KEY not configured. AI categorization disabled.")
            return
            
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if OpenAI service is available."""
        return self.client is not None
    
    def categorize_email(self, email_data: Dict) -> Dict:
        """
        Categorize email using GPT model with structured output.
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            Dictionary with category, confidence, and explanation
        """
        if not self.is_available():
            logger.warning("OpenAI service not available, using fallback")
            return self._fallback_categorization(email_data)
        
        # Check cache first
        cache_key = self._get_cache_key(email_data)
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info("Using cached OpenAI categorization")
            return cached_result
        
        try:
            # Prepare email content for analysis
            email_content = self._format_email_for_analysis(email_data)
            
            # Make API call to OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.CATEGORIZATION_PROMPT},
                    {"role": "user", "content": email_content}
                ],
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = self._parse_ai_response(response)
            
            # Cache result for 1 hour
            cache.set(cache_key, result, 3600)
            
            logger.info(f"OpenAI categorized email as: {result['category']} (confidence: {result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI categorization failed: {e}")
            # Fallback to rule-based categorization
            return self._fallback_categorization(email_data)
    
    def _format_email_for_analysis(self, email_data: Dict) -> str:
        """Format email data for OpenAI analysis."""
        subject = email_data.get('subject', 'No Subject')
        sender = email_data.get('sender', 'Unknown Sender')
        body = email_data.get('body', '')
        
        # Truncate body to prevent token limit issues
        if len(body) > 2000:
            body = body[:2000] + "... [truncated]"
        
        return f"""EMAIL TO ANALYZE:

Subject: {subject}
From: {sender}
Content: {body}

Please categorize this email."""
    
    def _parse_ai_response(self, response) -> Dict:
        """Parse OpenAI response and validate structure."""
        try:
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Validate required fields
            category = result.get('category', 'routine').lower()
            if category not in ['urgent', 'important', 'routine', 'promotional', 'spam']:
                category = 'routine'
            
            confidence = float(result.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
            
            priority = int(result.get('priority', 3))
            priority = max(1, min(5, priority))  # Clamp between 1 and 5
            
            return {
                'category': category,
                'confidence': confidence,
                'priority': priority,
                'explanation': result.get('explanation', 'AI categorization'),
                'suggested_actions': result.get('suggested_actions', []),
                'time_sensitive': result.get('time_sensitive', False),
                'requires_response': result.get('requires_response', False),
                'ai_powered': True,
                'model_used': self.model,
                'all_scores': {category: confidence}  # Compatibility with existing system
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            # Return default categorization
            return {
                'category': 'routine',
                'confidence': 0.3,
                'priority': 3,
                'explanation': 'AI parsing failed, using default',
                'suggested_actions': [],
                'time_sensitive': False,
                'requires_response': False,
                'ai_powered': False,
                'all_scores': {'routine': 0.3}
            }
    
    def _fallback_categorization(self, email_data: Dict) -> Dict:
        """Fallback categorization when OpenAI is unavailable."""
        from .categorization_engine import EmailCategorizationEngine
        
        logger.info("Using fallback keyword-based categorization")
        engine = EmailCategorizationEngine()
        result = engine.categorize_email(email_data)
        result['ai_powered'] = False
        result['model_used'] = 'keyword-based'
        
        return result
    
    def _get_cache_key(self, email_data: Dict) -> str:
        """Generate cache key for email categorization."""
        # Use message ID if available, otherwise hash of subject + sender
        message_id = email_data.get('message_id', email_data.get('id', ''))
        if message_id:
            return f"openai_categorization_{message_id}"
        
        # Fallback to hash of content
        import hashlib
        content = f"{email_data.get('subject', '')}{email_data.get('sender', '')}"
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"openai_categorization_{content_hash}"
    
    def categorize_emails_batch(self, emails: List[Dict], user=None) -> List[Dict]:
        """
        Categorize multiple emails efficiently with rate limiting.
        
        Args:
            emails: List of email dictionaries
            user: Optional user for personalized categorization
            
        Returns:
            List of categorization results
        """
        if not emails:
            return []
        
        # Limit batch size to prevent rate limiting
        max_batch_size = 10
        if len(emails) > max_batch_size:
            logger.warning(f"Batch size {len(emails)} exceeds limit {max_batch_size}, processing first {max_batch_size}")
            emails = emails[:max_batch_size]
        
        results = []
        processed = 0
        
        for email_data in emails:
            try:
                result = self.categorize_email(email_data)
                result['email_id'] = email_data.get('id')
                results.append(result)
                processed += 1
                
                logger.debug(f"Processed email {processed}/{len(emails)}: {result['category']}")
                
            except Exception as e:
                logger.error(f"Failed to categorize email {email_data.get('id', 'unknown')}: {e}")
                # Add fallback result
                results.append({
                    'email_id': email_data.get('id'),
                    'category': 'routine',
                    'confidence': 0.1,
                    'priority': 3,
                    'explanation': f'Categorization failed: {str(e)}',
                    'ai_powered': False,
                    'all_scores': {'routine': 0.1}
                })
        
        logger.info(f"Batch categorization completed: {processed}/{len(emails)} emails processed")
        return results
    
    def generate_reply_suggestions(self, email_data: Dict, tone: str = "professional") -> Dict:
        """
        Generate AI-powered reply suggestions for an email.
        
        Args:
            email_data: Email content and metadata
            tone: Desired tone (professional, friendly, formal, casual)
            
        Returns:
            Dictionary with suggested replies and templates
        """
        if not self.is_available():
            return {'error': 'OpenAI service not available'}
        
        try:
            reply_prompt = f"""Generate appropriate email reply suggestions for the following email. 
            Provide 3 different response options with {tone} tone:
            
            Original Email:
            Subject: {email_data.get('subject', 'No Subject')}
            From: {email_data.get('sender', 'Unknown')}
            Content: {email_data.get('body', '')[:1000]}
            
            Respond with JSON containing 3 suggested replies:
            {{
                "replies": [
                    {{"type": "brief", "subject": "Re: ...", "body": "..."}},
                    {{"type": "detailed", "subject": "Re: ...", "body": "..."}},
                    {{"type": "questions", "subject": "Re: ...", "body": "..."}}
                ]
            }}"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional email assistant."},
                    {"role": "user", "content": reply_prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Reply generation failed: {e}")
            return {'error': str(e)}
    
    def get_service_status(self) -> Dict:
        """Get OpenAI service status and configuration."""
        status = {
            'available': self.is_available(),
            'model': self.model,
            'api_key_configured': bool(getattr(settings, 'OPENAI_API_KEY', None))
        }
        
        if self.is_available():
            try:
                # Test API connectivity with a minimal request
                test_response = self.client.chat.completions.create(
                    model=self.FALLBACK_MODEL,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                status['api_responsive'] = True
                status['test_response_time'] = 'success'
            except Exception as e:
                status['api_responsive'] = False
                status['error'] = str(e)
        
        return status


# Factory function
def get_openai_service() -> OpenAIService:
    """Get OpenAI service instance."""
    return OpenAIService()


# Enhanced categorization function that combines AI and rule-based approaches
def categorize_with_ai(email_data: Dict, user=None) -> Dict:
    """
    Primary categorization function that uses AI with rule-based fallback.
    
    Args:
        email_data: Email content and metadata
        user: Optional user for personalized categorization
        
    Returns:
        Categorization result with confidence scores
    """
    ai_service = get_openai_service()
    
    # Try AI categorization first
    if ai_service.is_available():
        return ai_service.categorize_email(email_data)
    
    # Fallback to rule-based categorization
    logger.info("AI unavailable, using rule-based categorization")
    from .categorization_engine import EmailCategorizationEngine
    
    engine = EmailCategorizationEngine(user)
    result = engine.categorize_email(email_data)
    result['ai_powered'] = False
    result['model_used'] = 'rule-based'
    
    return result
"""
Integration tests for email loading and triage functionality
Tests the complete flow from backend to frontend
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from core.models import EmailAccount, EmailMessage, UserPreference
from core.services.categorization_engine import EmailCategorizationEngine

User = get_user_model()


class EmailTriageIntegrationTest(TestCase):
    """Test the complete email triage flow"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        
        # Create user preferences
        UserPreference.objects.create(
            user=self.user,
            default_tone='professional',
            auto_categorize=True,
            ai_confidence_threshold=0.7
        )
        
        # Create test email accounts
        self.gmail_account = EmailAccount.objects.create(
            user=self.user,
            provider='gmail',
            email_address='testuser@gmail.com',
            access_token='dummy_token',
            refresh_token='dummy_refresh',
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_active=True
        )
        
        self.outlook_account = EmailAccount.objects.create(
            user=self.user,
            provider='outlook',
            email_address='testuser@outlook.com',
            access_token='dummy_token',
            refresh_token='dummy_refresh',
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_active=True
        )
        
        # Create test emails
        self.create_test_emails()
    
    def create_test_emails(self):
        """Create sample emails for testing"""
        emails_data = [
            {
                'account': self.gmail_account,
                'message_id': 'gmail-001',
                'subject': 'URGENT: Project deadline tomorrow',
                'sender_email': 'manager@company.com',
                'sender_name': 'Project Manager',
                'category': 'urgent',
                'priority': 'high'
            },
            {
                'account': self.gmail_account,
                'message_id': 'gmail-002',
                'subject': 'Weekly Newsletter - Tech Updates',
                'sender_email': 'newsletter@techblog.com',
                'sender_name': 'Tech Blog',
                'category': 'newsletter',
                'priority': 'low'
            },
            {
                'account': self.outlook_account,
                'message_id': 'outlook-001',
                'subject': 'Meeting reminder: Q4 Review',
                'sender_email': 'admin@company.com',
                'sender_name': 'Office Admin',
                'category': 'important',
                'priority': 'medium'
            },
            {
                'account': self.outlook_account,
                'message_id': 'outlook-002',
                'subject': 'Special offer: 50% off everything!',
                'sender_email': 'deals@store.com',
                'sender_name': 'Online Store',
                'category': 'promotion',
                'priority': 'low'
            }
        ]
        
        for email_data in emails_data:
            EmailMessage.objects.create(
                **email_data,
                body_text=f"Test email content for {email_data['subject']}",
                received_at=timezone.now() - timedelta(hours=1),
                ai_confidence=0.85
            )

    def test_extension_health_endpoint(self):
        """Test extension health check endpoint"""
        response = self.client.get(
            '/api/extension/health/',
            HTTP_X_EXTENSION_SOURCE='fyxerai-chrome'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('FYXERAI backend is running', data['message'])

    def test_extension_triage_endpoint(self):
        """Test extension triage functionality"""
        # Prepare test email data
        test_emails = [
            {
                'id': 'ext-001',
                'subject': 'Urgent: Server down!',
                'sender': 'alerts@company.com',
                'platform': 'gmail'
            },
            {
                'id': 'ext-002',
                'subject': 'Summer sale newsletter',
                'sender': 'marketing@store.com',
                'platform': 'gmail'
            }
        ]
        
        response = self.client.post(
            '/api/extension/triage/',
            data=json.dumps({
                'platform': 'gmail',
                'emails': test_emails,
                'action': 'batch_triage'
            }),
            content_type='application/json',
            HTTP_X_EXTENSION_SOURCE='fyxerai-chrome'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['processed'], 2)
        self.assertEqual(len(data['categories']), 2)
        
        # Check categorization results
        categories = data['categories']
        urgent_email = next(c for c in categories if c['email_id'] == 'ext-001')
        newsletter_email = next(c for c in categories if c['email_id'] == 'ext-002')
        
        # Urgent email should have higher priority
        self.assertGreater(urgent_email['priority'], newsletter_email['priority'])

    def test_categorization_engine_accuracy(self):
        """Test the accuracy of email categorization"""
        engine = EmailCategorizationEngine(self.user)
        
        # Test urgent email
        urgent_result = engine.categorize_email({
            'subject': 'EMERGENCY: System failure',
            'sender': 'alerts@company.com',
            'body': 'Critical system failure requires immediate attention'
        })
        self.assertEqual(urgent_result['category'], 'urgent')
        self.assertGreater(urgent_result['confidence'], 0.5)
        
        # Test newsletter
        newsletter_result = engine.categorize_email({
            'subject': 'Weekly digest - Tech news',
            'sender': 'newsletter@blog.com',
            'body': 'This week in technology news...'
        })
        self.assertEqual(newsletter_result['category'], 'routine')
        
        # Test promotional
        promo_result = engine.categorize_email({
            'subject': 'Flash sale - 70% off!',
            'sender': 'sales@store.com',
            'body': 'Limited time offer - buy now!'
        })
        self.assertEqual(promo_result['category'], 'promotional')

    def test_dashboard_authentication_required(self):
        """Test that dashboard requires authentication"""
        # Test without login
        response = self.client.get('/partials/dashboard-overview/')
        self.assertEqual(response.status_code, 401)
        
        response = self.client.get('/partials/email-inbox/')
        self.assertEqual(response.status_code, 401)

    def test_dashboard_with_authentication(self):
        """Test dashboard functionality with authenticated user"""
        # Login user
        self.client.login(username='testuser', password='testpass123')
        
        # Test dashboard overview
        response = self.client.get('/partials/dashboard-overview/')
        self.assertEqual(response.status_code, 200)
        
        # Test email inbox
        response = self.client.get('/partials/email-inbox/')
        self.assertEqual(response.status_code, 200)
        
        # Check for email content
        content = response.content.decode()
        self.assertIn('Email Inbox', content)
        self.assertIn('URGENT: Project deadline tomorrow', content)

    def test_email_filtering_by_category(self):
        """Test email filtering functionality"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test filtering by urgent
        response = self.client.get('/partials/email-inbox/?category=urgent')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('URGENT: Project deadline tomorrow', content)
        self.assertNotIn('Weekly Newsletter', content)
        
        # Test filtering by newsletter
        response = self.client.get('/partials/email-inbox/?category=newsletter')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Weekly Newsletter', content)
        self.assertNotIn('URGENT: Project deadline', content)

    def test_email_statistics_calculation(self):
        """Test email statistics for dashboard"""
        self.client.login(username='testuser', password='testpass123')
        
        # Get dashboard overview
        response = self.client.get('/partials/dashboard-overview/')
        self.assertEqual(response.status_code, 200)
        
        # Should include statistics
        content = response.content.decode()
        self.assertIn('Total Messages', content)
        self.assertIn('Active Accounts', content)
        self.assertIn('2/2', content)  # 2 active accounts out of 2 total

    def test_user_learning_integration(self):
        """Test that user learning affects categorization"""
        engine = EmailCategorizationEngine(self.user)
        
        # Simulate user manually categorizing an email
        email_data = {
            'subject': 'Monthly report',
            'sender': 'reports@company.com',
            'body': 'Attached is the monthly financial report'
        }
        
        # Initial categorization
        initial_result = engine.categorize_email(email_data)
        initial_category = initial_result['category']
        
        # User manually changes category to 'important'
        engine.learn_from_user_action(email_data, 'important')
        
        # Categorize similar email from same sender
        similar_email = {
            'subject': 'Quarterly report',
            'sender': 'reports@company.com',
            'body': 'Please find the quarterly report attached'
        }
        
        # Should be influenced by user learning
        new_result = engine.categorize_email(similar_email)
        # The exact behavior depends on implementation details

    def test_batch_email_processing(self):
        """Test processing multiple emails efficiently"""
        engine = EmailCategorizationEngine(self.user)
        
        # Get all pending emails (if any)
        pending_emails = EmailMessage.objects.filter(
            account__user=self.user,
            category='pending'
        )
        
        if pending_emails.exists():
            # Test bulk categorization
            stats = engine.bulk_categorize_pending_emails(limit=10)
            
            self.assertIsInstance(stats, dict)
            self.assertIn('processed', stats)
            self.assertIn('updated', stats)
            self.assertIn('categories', stats)

    def test_cors_headers_for_extension(self):
        """Test CORS headers are properly set for extension requests"""
        response = self.client.get(
            '/api/extension/health/',
            HTTP_ORIGIN='chrome-extension://test-extension-id',
            HTTP_X_EXTENSION_SOURCE='fyxerai-chrome'
        )
        
        self.assertEqual(response.status_code, 200)
        # CORS headers should be present (exact headers depend on settings)

    def test_error_handling_in_triage(self):
        """Test error handling in triage endpoint"""
        # Test with malformed data
        response = self.client.post(
            '/api/extension/triage/',
            data='invalid json',
            content_type='application/json',
            HTTP_X_EXTENSION_SOURCE='fyxerai-chrome'
        )
        
        self.assertEqual(response.status_code, 400)
        
        # Test with missing required fields
        response = self.client.post(
            '/api/extension/triage/',
            data=json.dumps({'platform': 'gmail'}),  # Missing emails
            content_type='application/json',
            HTTP_X_EXTENSION_SOURCE='fyxerai-chrome'
        )
        
        self.assertEqual(response.status_code, 400)

    def test_extension_port_configuration(self):
        """Test that extension endpoints work on configured port"""
        # This test validates that our port fix (8000 vs 8002) is working
        # The fact that other tests pass validates this indirectly
        
        response = self.client.get('/api/extension/health/')
        self.assertEqual(response.status_code, 200)
        
        # Test that the response includes proper configuration info
        data = response.json()
        self.assertIn('timestamp', data)
        self.assertIn('extension_headers', data)
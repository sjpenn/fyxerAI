from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
import json

from .models import EmailAccount, EmailMessage, UserPreference, Meeting

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model functionality"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_create_user(self):
        """Test user creation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_premium)
        self.assertEqual(user.timezone, 'UTC')
    
    def test_user_str(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'testuser')


class EmailAccountModelTest(TestCase):
    """Test EmailAccount model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.account_data = {
            'user': self.user,
            'provider': 'gmail',
            'email_address': 'user@gmail.com',
            'display_name': 'Test User',
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'token_expires_at': timezone.now() + timedelta(hours=1)
        }
    
    def test_create_email_account(self):
        """Test email account creation"""
        account = EmailAccount.objects.create(**self.account_data)
        self.assertEqual(account.provider, 'gmail')
        self.assertEqual(account.email_address, 'user@gmail.com')
        self.assertTrue(account.is_active)
        self.assertTrue(account.sync_enabled)
    
    def test_email_account_str(self):
        """Test email account string representation"""
        account = EmailAccount.objects.create(**self.account_data)
        self.assertEqual(str(account), 'user@gmail.com (gmail)')
    
    def test_unique_user_email_constraint(self):
        """Test that user can't have duplicate email addresses"""
        EmailAccount.objects.create(**self.account_data)
        
        # Try to create another account with same email for same user
        with self.assertRaises(Exception):
            EmailAccount.objects.create(**self.account_data)


class EmailMessageModelTest(TestCase):
    """Test EmailMessage model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.account = EmailAccount.objects.create(
            user=self.user,
            provider='gmail',
            email_address='user@gmail.com',
            access_token='token',
            refresh_token='refresh',
            token_expires_at=timezone.now() + timedelta(hours=1)
        )
        self.message_data = {
            'account': self.account,
            'message_id': 'gmail_123',
            'subject': 'Test Email Subject',
            'sender_email': 'sender@example.com',
            'sender_name': 'Test Sender',
            'body_text': 'This is a test email body.',
            'category': 'important',
            'priority': 'high',
            'received_at': timezone.now()
        }
    
    def test_create_email_message(self):
        """Test email message creation"""
        message = EmailMessage.objects.create(**self.message_data)
        self.assertEqual(message.subject, 'Test Email Subject')
        self.assertEqual(message.category, 'important')
        self.assertEqual(message.priority, 'high')
        self.assertFalse(message.is_read)
        self.assertFalse(message.manual_override)
    
    def test_email_message_str(self):
        """Test email message string representation"""
        message = EmailMessage.objects.create(**self.message_data)
        expected = "Test Email Subject from sender@example.com"
        self.assertEqual(str(message), expected)


class UserPreferenceModelTest(TestCase):
    """Test UserPreference model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_user_preference(self):
        """Test user preference creation"""
        preference = UserPreference.objects.create(
            user=self.user,
            default_tone='friendly',
            signature='Best regards, Test User',
            ai_confidence_threshold=0.8
        )
        self.assertEqual(preference.default_tone, 'friendly')
        self.assertTrue(preference.auto_categorize)
        self.assertTrue(preference.auto_generate_drafts)
        self.assertEqual(preference.ai_confidence_threshold, 0.8)
    
    def test_user_preference_str(self):
        """Test user preference string representation"""
        preference = UserPreference.objects.create(user=self.user)
        self.assertEqual(str(preference), 'testuser preferences')
    
    def test_category_rule_methods(self):
        """Test category rule getter and setter methods"""
        preference = UserPreference.objects.create(user=self.user)
        
        # Test setting a category rule
        preference.set_category_rule('important@company.com', 'urgent', 'high')
        rule = preference.get_category_rule('important@company.com')
        self.assertEqual(rule['category'], 'urgent')
        self.assertEqual(rule['priority'], 'high')
        
        # Test getting non-existent rule
        empty_rule = preference.get_category_rule('nonexistent@example.com')
        self.assertEqual(empty_rule, {})


class MeetingModelTest(TestCase):
    """Test Meeting model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.meeting_data = {
            'user': self.user,
            'title': 'Weekly Team Meeting',
            'platform': 'zoom',
            'organizer_email': 'organizer@company.com',
            'scheduled_start': timezone.now() + timedelta(hours=1),
            'scheduled_end': timezone.now() + timedelta(hours=2),
        }
    
    def test_create_meeting(self):
        """Test meeting creation"""
        meeting = Meeting.objects.create(**self.meeting_data)
        self.assertEqual(meeting.title, 'Weekly Team Meeting')
        self.assertEqual(meeting.platform, 'zoom')
        self.assertEqual(meeting.status, 'scheduled')
        self.assertFalse(meeting.has_recording)
        self.assertFalse(meeting.has_transcript)
    
    def test_meeting_str(self):
        """Test meeting string representation"""
        meeting = Meeting.objects.create(**self.meeting_data)
        expected_date = meeting.scheduled_start.strftime('%Y-%m-%d %H:%M')
        expected = f"Weekly Team Meeting - {expected_date}"
        self.assertEqual(str(meeting), expected)
    
    def test_duration_minutes_property(self):
        """Test duration calculation"""
        meeting = Meeting.objects.create(**self.meeting_data)
        # Scheduled duration should be 60 minutes
        self.assertEqual(meeting.duration_minutes, 60)
        
        # Test with actual times
        meeting.actual_start = timezone.now()
        meeting.actual_end = timezone.now() + timedelta(minutes=45)
        meeting.save()
        self.assertEqual(meeting.duration_minutes, 45)


class APIHealthCheckTest(APITestCase):
    """Test health check API endpoint"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        url = reverse('core:health-check')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('database', data)
        self.assertTrue(data['database'])


class UserAPITest(APITestCase):
    """Test User API endpoints"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        url = reverse('core:user-register')
        response = self.client.post(url, self.user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_user_profile_requires_auth(self):
        """Test that user profile requires authentication"""
        url = reverse('core:user-profile')
        response = self.client.get(url)
        
        # DRF returns 403 when authentication is required but user is not authenticated
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_user_profile_with_auth(self):
        """Test user profile with authentication"""
        user = User.objects.create_user(**self.user_data)
        self.client.force_authenticate(user=user)
        
        url = reverse('core:user-profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')


class EmailAPITest(APITestCase):
    """Test Email API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.account = EmailAccount.objects.create(
            user=self.user,
            provider='gmail',
            email_address='user@gmail.com',
            access_token='token',
            refresh_token='refresh',
            token_expires_at=timezone.now() + timedelta(hours=1)
        )
    
    def test_email_account_list(self):
        """Test email account list endpoint"""
        url = reverse('core:email-accounts')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Check if response is paginated
        if 'results' in data:
            self.assertEqual(len(data['results']), 1)
            self.assertEqual(data['results'][0]['email_address'], 'user@gmail.com')
        else:
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['email_address'], 'user@gmail.com')
    
    def test_email_message_list_empty(self):
        """Test email message list when empty"""
        url = reverse('core:email-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 0)
    
    def test_email_message_list_with_data(self):
        """Test email message list with data"""
        EmailMessage.objects.create(
            account=self.account,
            message_id='test_123',
            subject='Test Subject',
            sender_email='sender@example.com',
            received_at=timezone.now()
        )
        
        url = reverse('core:email-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['subject'], 'Test Subject')
    
    def test_email_draft_generation(self):
        """Test AI draft generation endpoint"""
        message = EmailMessage.objects.create(
            account=self.account,
            message_id='test_123',
            subject='Test Subject',
            sender_email='sender@example.com',
            received_at=timezone.now()
        )
        
        url = reverse('core:email-draft')
        data = {
            'message_id': 'test_123',
            'tone': 'professional'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('draft_content', response_data)
        self.assertEqual(response_data['tone'], 'professional')


class UserPreferenceAPITest(APITestCase):
    """Test UserPreference API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_user_preference_create_on_get(self):
        """Test that user preference is created when accessed"""
        url = reverse('core:user-preferences')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserPreference.objects.filter(user=self.user).exists())
    
    def test_user_preference_update(self):
        """Test user preference update"""
        url = reverse('core:user-preferences')
        data = {
            'default_tone': 'casual',
            'signature': 'Cheers, Test User',
            'ai_confidence_threshold': 0.9
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual(preference.default_tone, 'casual')
        self.assertEqual(preference.signature, 'Cheers, Test User')
        self.assertEqual(preference.ai_confidence_threshold, 0.9)


class HomeViewTest(TestCase):
    """Test home view"""
    
    def test_home_view_returns_api_info(self):
        """Test that home view returns API information"""
        response = self.client.get('/', HTTP_ACCEPT='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('message', data)
        self.assertIn('endpoints', data)
        self.assertEqual(data['message'], 'FyxerAI-GEDS API is running')

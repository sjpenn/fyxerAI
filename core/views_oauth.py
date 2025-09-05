"""
OAuth views for Gmail and Outlook account connection
"""
import logging
from urllib.parse import urlencode
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception:
    Request = None
    Credentials = None
    Flow = None
    build = None
    class HttpError(Exception):
        pass

from .models import EmailAccount
from .services.notification_service import RealTimeNotificationService
from .tasks import sync_user_accounts
from django.conf import settings

logger = logging.getLogger(__name__)

# Gmail OAuth2 scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


@login_required
def gmail_oauth_login(request):
    """Initiate Gmail OAuth flow"""
    if Flow is None:
        messages.error(request, "Google API client is not installed. Please install dependencies.")
        return redirect('core:home')
    logger.info(f"Gmail OAuth login initiated for user {request.user.id}")
    logger.debug(f"User authenticated: {request.user.is_authenticated}")
    logger.debug(f"Session key before OAuth: {request.session.session_key}")
    
    try:
        # Store user ID in session for callback verification
        request.session['oauth_user_id'] = request.user.id
        
        # Create a Flow instance for OAuth2
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [request.build_absolute_uri(reverse('core:gmail_oauth_callback'))],
                }
            },
            scopes=GMAIL_SCOPES
        )
        
        flow.redirect_uri = request.build_absolute_uri(reverse('core:gmail_oauth_callback'))
        
        # Generate a random state parameter for CSRF protection
        state = str(uuid.uuid4())
        request.session['oauth_state'] = state
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            # Ensure refresh_token and account choice
            prompt='consent select_account'
        )
        
        # Force session save before redirect
        request.session.save()
        
        logger.info(f"Initiating Gmail OAuth for user {request.user.id}, state: {state}")
        logger.debug(f"Session saved with oauth_state and oauth_user_id")
        return HttpResponseRedirect(authorization_url)
        
    except Exception as e:
        logger.error(f"Gmail OAuth login error: {str(e)}")
        messages.error(request, "Failed to initiate Gmail connection. Please try again.")
        return redirect('core:home')


@login_required
def gmail_oauth_callback(request):
    """Handle Gmail OAuth callback"""
    if Credentials is None or Request is None:
        messages.error(request, "Google API client is not installed. Please install dependencies.")
        return redirect('core:home')
    logger.info(f"Gmail OAuth callback called for user {request.user.id}")
    logger.info(f"User authenticated: {request.user.is_authenticated}")
    logger.info(f"Session key: {request.session.session_key}")
    logger.info(f"GET parameters: {dict(request.GET)}")
    
    # Debug: Check user authentication state
    if not request.user.is_authenticated:
        logger.error(f"User not authenticated in OAuth callback. Session key: {request.session.session_key}")
        
        # Try to recover user from session
        oauth_user_id = request.session.get('oauth_user_id')
        if oauth_user_id:
            logger.info(f"Attempting to recover user {oauth_user_id} from session")
            from django.contrib.auth import get_user_model, login
            try:
                User = get_user_model()
                user = User.objects.get(id=oauth_user_id)
                login(request, user)
                logger.info(f"Successfully recovered and logged in user {oauth_user_id}")
            except Exception as e:
                logger.error(f"Failed to recover user {oauth_user_id}: {str(e)}")
                messages.error(request, "Authentication required. Please login and try again.")
                return redirect('core:login')
        else:
            logger.error(f"No oauth_user_id found in session. Redirecting to login.")
            messages.error(request, "Authentication required. Please login and try again.")
            return redirect('core:login')
    
    try:
        # Verify state parameter for CSRF protection
        state = request.GET.get('state')
        session_state = request.session.get('oauth_state')
        
        logger.debug(f"State verification - Received: {state}, Expected: {session_state}")
        
        if not state or state != session_state:
            logger.warning(f"OAuth state mismatch for user {request.user.id}. Received: {state}, Expected: {session_state}")
            messages.error(request, "Invalid OAuth state. Please try connecting again.")
            return redirect('core:home')
        
        # Clean up OAuth session state
        if 'oauth_state' in request.session:
            del request.session['oauth_state']
        if 'oauth_user_id' in request.session:
            del request.session['oauth_user_id']
        
        # Check for authorization code
        authorization_code = request.GET.get('code')
        if not authorization_code:
            error = request.GET.get('error')
            logger.warning(f"Gmail OAuth denied for user {request.user.id}: {error}")
            messages.error(request, "Gmail connection was cancelled or denied.")
            return redirect('core:home')
        
        # Exchange authorization code for access token
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [request.build_absolute_uri(reverse('core:gmail_oauth_callback'))],
                }
            },
            scopes=GMAIL_SCOPES
        )
        
        flow.redirect_uri = request.build_absolute_uri(reverse('core:gmail_oauth_callback'))
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        
        credentials = flow.credentials
        
        # Get user profile information
        user_info = get_gmail_user_info(credentials)
        if not user_info:
            messages.error(request, "Failed to retrieve Gmail account information.")
            return redirect('core:home')
        
        email_address = user_info.get('email')
        display_name = user_info.get('name', email_address)
        
        # Check if account already exists for this user
        existing_account = EmailAccount.objects.filter(
            user=request.user,
            email_address=email_address
        ).first()
        
        if existing_account:
            # Update existing account
            logger.info(f"Updating existing Gmail account {email_address} for user {request.user.id}")
            existing_account.access_token = existing_account.encrypt_token(credentials.token)
            existing_account.refresh_token = existing_account.encrypt_token(credentials.refresh_token)
            if credentials.expiry:
                existing_account.token_expires_at = credentials.expiry.replace(tzinfo=timezone.utc)
            else:
                existing_account.token_expires_at = timezone.now() + timedelta(hours=1)
            existing_account.display_name = display_name
            existing_account.is_active = True
            existing_account.save()
            
            logger.info(f"Successfully updated Gmail account {email_address}")
            messages.success(request, f"Gmail account {email_address} has been updated successfully.")
            try:
                RealTimeNotificationService().notify_account_connected(existing_account)
            except Exception as notify_err:
                logger.warning(f"Failed to send websocket account_connected notification: {notify_err}")
        else:
            # Create new account
            logger.info(f"Creating new Gmail account {email_address} for user {request.user.id}")
            new_account = EmailAccount.objects.create(
                user=request.user,
                provider='gmail',
                email_address=email_address,
                display_name=display_name,
                access_token=EmailAccount().encrypt_token(credentials.token),
                refresh_token=EmailAccount().encrypt_token(credentials.refresh_token),
                token_expires_at=credentials.expiry.replace(tzinfo=timezone.utc) if credentials.expiry else timezone.now() + timedelta(hours=1),
                is_active=True,
            )
            
            logger.info(f"Successfully created Gmail account {email_address} with ID {new_account.id}")
            messages.success(request, f"Gmail account {email_address} has been connected successfully.")
            try:
                RealTimeNotificationService().notify_account_connected(new_account)
            except Exception as notify_err:
                logger.warning(f"Failed to send websocket account_connected notification: {notify_err}")
        
        logger.info(f"Gmail account {email_address} connected for user {request.user.id}")
        
        # Set session flag for dashboard refresh
        request.session['account_connected'] = True
        request.session['connected_account_email'] = email_address
        
        # Force session save to ensure persistence
        request.session.save()
        
        logger.debug(f"Session saved with account_connected flag for user {request.user.id}")
        
        # Queue a background sync so unread counts and inbox populate
        try:
            sync_user_accounts.delay(request.user.id, True)
        except Exception as e:
            logger.warning(f"Failed to queue background sync after OAuth: {e}")
        
        # Redirect to home with success parameter for dashboard refresh
        return redirect('core:home')
        
    except Exception as e:
        logger.error(f"Gmail OAuth callback error for user {request.user.id}: {str(e)}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        messages.error(request, "Failed to connect Gmail account. Please try again.")
        return redirect('core:home')


@login_required
@require_http_methods(["POST"])
def disconnect_email_account(request, account_id):
    """Disconnect an email account"""
    try:
        account = get_object_or_404(
            EmailAccount,
            id=account_id,
            user=request.user
        )
        
        email_address = account.email_address
        provider = account.get_provider_display()
        
        # Delete the account
        account.delete()
        
        messages.success(request, f"{provider} account {email_address} has been disconnected.")
        logger.info(f"Email account {email_address} disconnected for user {request.user.id}")
        
        # Return HTMX-friendly response if requested
        if request.headers.get('HX-Request'):
            return HttpResponseRedirect(reverse('core:account_menu'))
        
        return redirect('core:home')
        
    except Exception as e:
        logger.error(f"Account disconnect error: {str(e)}")
        messages.error(request, "Failed to disconnect account. Please try again.")
        
        if request.headers.get('HX-Request'):
            return HttpResponseRedirect(reverse('core:account_menu'))
        
        return redirect('core:home')


@login_required
def add_account_form(request):
    """Display form to add new email accounts"""
    return render(request, 'oauth/add_account.html', {
        'google_client_id_configured': bool(settings.GOOGLE_CLIENT_ID),
        'microsoft_client_id_configured': bool(settings.MICROSOFT_CLIENT_ID),
    })


def oauth_debug_view(request):
    """Debug OAuth configuration and status"""
    accounts = []
    accounts_count = 0
    
    if request.user.is_authenticated:
        accounts = EmailAccount.objects.filter(user=request.user)
        accounts_count = accounts.count()
    
    context = {
        'google_client_id_configured': bool(settings.GOOGLE_CLIENT_ID),
        'google_client_secret_configured': bool(settings.GOOGLE_CLIENT_SECRET),
        'base_url': getattr(settings, 'BASE_URL', 'http://localhost:8000'),
        'callback_url': f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/auth/gmail/callback/",
        'accounts': accounts,
        'accounts_count': accounts_count,
    }
    
    return render(request, 'oauth/debug.html', context)


def get_gmail_user_info(credentials):
    """Get Gmail user profile information"""
    try:
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
        return None
    except Exception as e:
        logger.error(f"Failed to get user info: {str(e)}")
        return None


def refresh_gmail_token(account):
    """Refresh Gmail access token using refresh token"""
    try:
        credentials = Credentials(
            token=account.decrypt_token(account.access_token),
            refresh_token=account.decrypt_token(account.refresh_token),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        # Refresh the token
        credentials.refresh(Request())
        
        # Update the account with new token
        account.access_token = account.encrypt_token(credentials.token)
        account.token_expires_at = timezone.now() + timedelta(seconds=3600)  # Usually 1 hour
        account.save()
        
        logger.info(f"Refreshed token for Gmail account {account.email_address}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to refresh token for {account.email_address}: {str(e)}")
        return False

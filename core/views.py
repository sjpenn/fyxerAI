import logging

from django.contrib.auth import get_user_model, login
from django.contrib import messages
from django.db import connection
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone
from rest_framework import generics, permissions, status
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmailAccount, EmailMessage, Meeting, UserPreference
from .serializers import (CategoryUpdateSerializer, EmailAccountSerializer,
                          EmailDraftSerializer, EmailMessageDetailSerializer,
                          EmailMessageSerializer, HealthCheckSerializer,
                          MeetingDetailSerializer, MeetingSerializer,
                          UserPreferenceSerializer, UserSerializer)
from .services.openai_service import get_openai_service
from .services.gmail_service import get_gmail_service

logger = logging.getLogger(__name__)

User = get_user_model()


def login_view(request):
    """Simple login page that redirects to Django admin login"""
    next_url = request.GET.get('next', '/')
    admin_login_url = f"/admin/login/?next={next_url}"
    return HttpResponseRedirect(admin_login_url)


def signup_view(request):
    """Simple user registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Basic validation
        if not all([username, email, password1, password2]):
            messages.error(request, 'All fields are required.')
            return render(request, 'auth/signup.html')
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/signup.html')
        
        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'auth/signup.html')
        
        # Check if user exists
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'auth/signup.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/signup.html')
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1
            )
            
            # Auto-login after registration
            login(request, user)
            messages.success(request, f'Welcome to FYXERAI, {username}! Your account has been created successfully.')
            return redirect('core:home')
            
        except Exception as e:
            logger.error(f"User registration error: {str(e)}")
            messages.error(request, 'An error occurred while creating your account. Please try again.')
            return render(request, 'auth/signup.html')
    
    return render(request, 'auth/signup.html')


# Template Views
def home(request):
    """Dashboard home view with HTMX integration or API root."""
    logger.info(f"Home view accessed by user: {request.user.id if request.user.is_authenticated else 'Anonymous'}")
    
    # Check if this is an API request (e.g., from tests or API clients)
    if request.headers.get('Accept') == 'application/json' or 'api' in request.path:
        # Return API information for programmatic access
        from django.http import JsonResponse
        return JsonResponse({
            "message": "FyxerAI-GEDS API is running",
            "version": "1.0.0",
            "endpoints": {
                "health": "/api/health/",
                "auth": {
                    "register": "/api/auth/register/",
                    "profile": "/api/auth/profile/",
                    "preferences": "/api/auth/preferences/"
                },
                "emails": {
                    "list": "/api/emails/",
                    "detail": "/api/emails/{id}/",
                    "triage": "/api/emails/{id}/triage/",
                    "reply": "/api/emails/reply/"
                },
                "email_accounts": {
                    "list": "/api/email-accounts/",
                    "detail": "/api/email-accounts/{id}/"
                },
                "meetings": {
                    "list": "/api/meetings/",
                    "detail": "/api/meetings/{id}/",
                    "summary": "/api/meetings/{id}/summary/"
                }
            }
        })
    
    # Check for OAuth success and prepare dashboard context
    account_connected = request.session.pop('account_connected', False)
    connected_account_email = request.session.pop('connected_account_email', None)
    
    if account_connected:
        logger.info(f"OAuth success detected for user {request.user.id}, account: {connected_account_email}")
    
    # Return HTML template for browser access
    context = {
        "user": request.user if request.user.is_authenticated else None,
        "version": "1.0.0",
        "page_title": "Dashboard",
        "active_section": "dashboard",
        "account_connected": account_connected,
        "connected_account_email": connected_account_email,
    }
    
    logger.debug(f"Dashboard context: account_connected={account_connected}, email={connected_account_email}")
    return render(request, "dashboard.html", context)


def components_showcase(request):
    """Components showcase view."""
    return render(request, "components-showcase.html")


# HTMX Partial Views
def email_inbox_partial(request):
    """HTMX partial view for email inbox"""
    if not request.user.is_authenticated:
        context = {"user": request.user}
        return render(request, "partials/unauthenticated.html", context)

    # Filter parameters
    category = request.GET.get("category", "")
    account_id = request.GET.get("account", "")

    # Get user's email messages
    messages_qs = EmailMessage.objects.filter(account__user=request.user)

    if category:
        messages_qs = messages_qs.filter(category=category)
    if account_id:
        messages_qs = messages_qs.filter(account_id=account_id)

    messages = messages_qs.order_by("-received_at")[:20]

    context = {
        "messages": messages,
        "selected_category": category,
        "selected_account": account_id,
    }

    return render(request, "partials/email_inbox.html", context)


def email_accounts_partial(request):
    """HTMX partial view for email accounts"""
    logger.debug(f"Email accounts partial requested by user: {request.user.id if request.user.is_authenticated else 'Anonymous'}")
    
    if not request.user.is_authenticated:
        logger.warning("Unauthenticated user attempting to access email accounts partial")
        # Return HTML content for unauthenticated users
        context = {"user": request.user}
        return render(request, "partials/unauthenticated.html", context)

    # Get all accounts (not just active ones) for debugging
    from django.db.models import Count, Q
    from datetime import timedelta
    week_ago = timezone.now() - timedelta(days=7)

    accounts = (
        EmailAccount.objects
        .filter(user=request.user)
        .annotate(
            total_count=Count('messages', distinct=True),
            unread_count=Count('messages', filter=Q(messages__is_read=False), distinct=True),
            week_count=Count('messages', filter=Q(messages__received_at__gte=week_ago), distinct=True),
        )
    )
    active_accounts = accounts.filter(is_active=True)
    
    logger.info(f"User {request.user.id} has {accounts.count()} total accounts, {active_accounts.count()} active")
    
    # Debug logging for each account
    for account in accounts:
        logger.debug(f"Account: {account.email_address}, Provider: {account.provider}, Active: {account.is_active}, Created: {account.created_at}")

    context = {
        "accounts": active_accounts,
        "user": request.user,
        "total_accounts": accounts.count(),
        "debug_mode": True,  # Enable debugging info in template
    }

    return render(request, "partials/email_accounts.html", context)


def email_stats_partial(request):
    """HTMX partial view for email statistics"""
    if not request.user.is_authenticated:
        context = {"user": request.user}
        return render(request, "partials/unauthenticated.html", context)

    from django.db.models import Count

    # Calculate statistics
    total_messages = EmailMessage.objects.filter(account__user=request.user).count()
    unread_messages = EmailMessage.objects.filter(
        account__user=request.user, is_read=False
    ).count()

    category_stats = (
        EmailMessage.objects.filter(account__user=request.user)
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    context = {
        "total_messages": total_messages,
        "unread_messages": unread_messages,
        "category_stats": category_stats,
    }

    return render(request, "partials/email_stats.html", context)


def dashboard_overview_partial(request):
    """HTMX partial view for dashboard overview"""
    if not request.user.is_authenticated:
        context = {"user": request.user}
        return render(request, "partials/unauthenticated.html", context)

    from datetime import datetime, timedelta

    from django.db.models import Count

    # Get today's date range
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    # Recent activity statistics
    recent_messages = EmailMessage.objects.filter(
        account__user=request.user, received_at__date__gte=week_ago
    ).count()

    recent_meetings = Meeting.objects.filter(
        user=request.user, scheduled_start__date__gte=week_ago
    ).count()

    # Account status
    total_accounts = EmailAccount.objects.filter(user=request.user).count()
    active_accounts = EmailAccount.objects.filter(
        user=request.user, is_active=True
    ).count()

    context = {
        "recent_messages": recent_messages,
        "recent_meetings": recent_meetings,
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "user": request.user,
    }

    return render(request, "partials/dashboard_overview.html", context)


def account_menu_partial(request):
    """HTMX partial view for nested account menu"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    from django.db.models import Count, Q
    accounts_qs = (
        EmailAccount.objects
        .filter(user=request.user, is_active=True)
        .annotate(
            unread_count=Count('messages', filter=Q(messages__is_read=False), distinct=True),
            total_count=Count('messages', distinct=True),
        )
        .order_by('provider', 'email_address')
    )
    # Optionally enrich with live unread counts from provider (Gmail)
    accounts = []
    try:
        from .services.gmail_service import get_gmail_service
        for acc in accounts_qs:
            acc.external_unread = None
            if acc.provider == 'gmail':
                svc = get_gmail_service(
                    acc.email_address,
                    scopes=['https://www.googleapis.com/auth/gmail.readonly']
                )
                if svc and svc.is_authenticated():
                    acc.external_unread = svc.get_unread_count()
            accounts.append(acc)
    except Exception:
        # If any error, fall back to plain queryset list
        accounts = list(accounts_qs)

    context = {"accounts": accounts}

    return render(request, "partials/account_menu.html", context)


# API Views
class UserCreateView(generics.CreateAPIView):
    """Create new user account"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@login_required
@require_http_methods(["GET"])
def gmail_message_detail(request, message_id):
    """Return Gmail message details by ID (JSON). Requires ?email=<address>."""
    email = request.GET.get('email')
    if not email:
        return JsonResponse({'error': 'email parameter required'}, status=400)
    try:
        svc = get_gmail_service(email, scopes=['https://www.googleapis.com/auth/gmail.readonly'])
        if not svc or not svc.is_authenticated():
            return JsonResponse({'error': 'gmail not authenticated'}, status=401)
        data = svc._process_message(message_id)
        if not data:
            return JsonResponse({'error': 'not found'}, status=404)
        return JsonResponse({'message': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def gmail_message_list(request):
    """Return Gmail messages (metadata-first). Params: email, days=7, limit=50"""
    email = request.GET.get('email')
    days = int(request.GET.get('days', 7))
    limit = int(request.GET.get('limit', 50))
    if not email:
        return JsonResponse({'error': 'email parameter required'}, status=400)
    try:
        svc = get_gmail_service(email, scopes=['https://www.googleapis.com/auth/gmail.readonly'])
        if not svc or not svc.is_authenticated():
            return JsonResponse({'error': 'gmail not authenticated'}, status=401)
        from django.utils import timezone as _tz
        from datetime import timedelta as _td
        msgs = svc.fetch_emails(since_date=_tz.now() - _td(days=days), max_results=limit, include_bodies=False)
        return JsonResponse({'messages': msgs})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class EmailAccountListCreateView(generics.ListCreateAPIView):
    """List user's email accounts or create new one"""

    serializer_class = EmailAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EmailAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EmailAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete specific email account"""

    serializer_class = EmailAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EmailAccount.objects.filter(user=self.request.user)


class EmailMessageListView(generics.ListAPIView):
    """List user's email messages with filtering"""

    serializer_class = EmailMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = EmailMessage.objects.filter(account__user=self.request.user)

        # Filter parameters
        category = self.request.query_params.get("category")
        priority = self.request.query_params.get("priority")
        is_read = self.request.query_params.get("is_read")
        account_id = self.request.query_params.get("account")

        if category:
            queryset = queryset.filter(category=category)
        if priority:
            queryset = queryset.filter(priority=priority)
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == "true")
        if account_id:
            queryset = queryset.filter(account_id=account_id)

        return queryset.order_by("-received_at")


class EmailMessageDetailView(generics.RetrieveUpdateAPIView):
    """Get or update specific email message"""

    serializer_class = EmailMessageDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EmailMessage.objects.filter(account__user=self.request.user)


class EmailMessageTriageView(APIView):
    """Manually update email category (triage)"""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            email = EmailMessage.objects.get(pk=pk, account__user=request.user)
        except EmailMessage.DoesNotExist:
            return Response(
                {"error": "Email not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CategoryUpdateSerializer(email, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(EmailMessageSerializer(email).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailDraftGenerateView(APIView):
    """Generate AI draft reply for email"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmailDraftSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            message_id = serializer.validated_data["message_id"]
            tone = serializer.validated_data.get("tone", "professional")
            additional_context = serializer.validated_data.get("additional_context", "")
            
            # Get the email message
            email_message = EmailMessage.objects.get(
                message_id=message_id,
                account__user=request.user
            )

            # Prepare email data for AI service
            email_data = {
                "subject": email_message.subject,
                "sender": email_message.sender_email,
                "body": email_message.body_text,
            }

            # Get AI service and generate suggestions
            ai_service = get_openai_service()
            if not ai_service.is_available():
                # Provide fallback templates when OpenAI is unavailable
                fallback_suggestions = {
                    "replies": [
                        {
                            "type": "brief",
                            "subject": f"Re: {email_message.subject}",
                            "body": f"Thank you for your email regarding '{email_message.subject}'. I will review and respond shortly."
                        },
                        {
                            "type": "detailed",
                            "subject": f"Re: {email_message.subject}",
                            "body": f"Thank you for reaching out about '{email_message.subject}'. I have received your message and will provide a detailed response after reviewing the matter thoroughly."
                        },
                        {
                            "type": "questions",
                            "subject": f"Re: {email_message.subject}",
                            "body": f"Thank you for your email about '{email_message.subject}'. Could you please provide more details so I can better assist you?"
                        }
                    ],
                    "ai_powered": False,
                    "note": "OpenAI service temporarily unavailable, using template responses"
                }
                
                return Response(
                    {
                        "suggestions": fallback_suggestions,
                        "draft_content": fallback_suggestions["replies"][0]["body"],
                        "tone": tone,
                        "generated_at": timezone.now(),
                    }
                )

            suggestions = ai_service.generate_reply_suggestions(email_data, tone)

            if "error" in suggestions:
                # Return fallback instead of error
                fallback_suggestions = {
                    "replies": [
                        {
                            "type": "brief",
                            "subject": f"Re: {email_message.subject}",
                            "body": f"Thank you for your email regarding '{email_message.subject}'. I will review and respond shortly."
                        }
                    ],
                    "ai_powered": False,
                    "error": f"AI service error: {suggestions.get('error', 'Unknown error')}"
                }
                return Response(
                    {
                        "suggestions": fallback_suggestions,
                        "draft_content": fallback_suggestions["replies"][0]["body"],
                        "tone": tone,
                        "generated_at": timezone.now(),
                    }
                )

            return Response(
                {
                    "suggestions": suggestions,
                    "draft_content": suggestions.get("replies", [{}])[0].get("body", ""),
                    "tone": tone,
                    "generated_at": timezone.now(),
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserPreferenceView(generics.RetrieveUpdateAPIView):
    """Get and update user preferences"""

    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        preference, created = UserPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference


class MeetingListCreateView(generics.ListCreateAPIView):
    """List user's meetings or create new one"""

    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Meeting.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MeetingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete specific meeting"""

    serializer_class = MeetingDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Meeting.objects.filter(user=self.request.user)


class MeetingSummaryView(APIView):
    """Get meeting summary and AI-generated content"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk, user=request.user)
        except Meeting.DoesNotExist:
            return Response(
                {"error": "Meeting not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "meeting_id": meeting.id,
                "title": meeting.title,
                "summary": meeting.summary,
                "action_items": meeting.action_items,
                "key_topics": meeting.key_topics,
                "follow_up_emails": meeting.follow_up_emails,
                "has_recording": meeting.has_recording,
                "has_transcript": meeting.has_transcript,
            }
        )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint for monitoring"""

    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = True
    except Exception:
        db_status = False

    # Check Redis connectivity (if configured)
    redis_status = True  # TODO: Implement Redis health check

    data = {
        "status": "healthy" if db_status else "unhealthy",
        "timestamp": timezone.now(),
        "version": "1.0.0",  # TODO: Get from package or settings
        "database": db_status,
        "redis": redis_status,
    }

    serializer = HealthCheckSerializer(data)
    return Response(serializer.data)


# Extension-compatible API views
class ExtensionTriageView(APIView):
    """Chrome/Outlook extension triage endpoint"""

    permission_classes = [
        permissions.AllowAny
    ]  # Allow unauthenticated for extension testing

    def post(self, request):
        try:
            platform = request.data.get("platform", "unknown")
            action = request.data.get("action", "")
            emails = request.data.get("emails", [])
            single_email = request.data.get("email", {})

            # Handle single email triage
            if action == "triage_single" and single_email:
                category = self.categorize_email(single_email)
                return Response(
                    {
                        "success": True,
                        "category": category,
                        "email_id": single_email.get("id", "unknown"),
                    }
                )

            # Handle bulk email triage
            categories = []
            for email_data in emails[:10]:  # Limit to 10 emails for testing
                category = self.categorize_email(email_data)
                categories.append(
                    {
                        "id": email_data.get("id", "unknown"),
                        "category": category,
                        "original_data": email_data,
                    }
                )

            return Response(
                {
                    "success": True,
                    "processed": len(categories),
                    "categories": categories,
                    "platform": platform,
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def categorize_email(self, email_data):
        """Simple email categorization logic"""
        subject = email_data.get('subject', '').lower()

        # Simple keyword-based categorization
        urgent_keywords = ["urgent", "asap", "emergency", "critical", "deadline"]
        important_keywords = ["meeting", "project", "report", "review", "approval"]
        spam_keywords = ["offer", "deal", "discount", "promotion", "winner"]

        # Check for urgent emails
        if any(keyword in subject for keyword in urgent_keywords):
            return "urgent"

        # Check for important emails
        if any(keyword in subject for keyword in important_keywords):
            return "important"

        # Check for spam
        if any(keyword in subject for keyword in spam_keywords):
            return "spam"

        # Default to routine
        return "routine"


class ExtensionDraftView(APIView):
    """Chrome/Outlook extension draft generation endpoint"""

    permission_classes = [
        permissions.AllowAny
    ]  # Allow unauthenticated for extension testing

    def post(self, request):
        try:
            platform = request.data.get("platform", "unknown")
            action = request.data.get("action", "")
            email_content = request.data.get("email_content", {})
            emails = request.data.get("emails", [])

            # Handle single draft generation
            if action == "generate_single_draft" and email_content:
                draft = self.generate_draft(email_content)
                return Response({"success": True, "draft": draft, "platform": platform})

            # Handle bulk draft generation
            drafts = []
            for email_data in emails[:5]:  # Limit to 5 drafts for testing
                draft = self.generate_draft(email_data)
                drafts.append(
                    {
                        "email_id": email_data.get("id", "unknown"),
                        "draft": draft,
                        "original_data": email_data,
                    }
                )

            return Response(
                {
                    "success": True,
                    "created": len(drafts),
                    "drafts": drafts,
                    "platform": platform,
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def generate_draft(self, email_data):
        """Simple draft generation logic"""
        subject = email_data.get("subject", "No Subject")
        sender = email_data.get("sender", "Unknown Sender")
        category = email_data.get("category", "routine")

        # Simple template-based draft generation
        if category == "urgent":
            draft = f"""Thank you for your urgent message regarding "{subject}".
            
I understand the importance of this matter and will prioritize it accordingly. I'll review the details and get back to you as soon as possible.

Best regards"""

        elif category == "important":
            draft = f"""Thank you for your email about "{subject}".
            
I've received your message and will give it the attention it deserves. I'll review the information and respond with my thoughts shortly.

Best regards"""

        elif category == "spam":
            draft = """Thank you for your email.
            
I'm not interested in this offer at this time.

Regards"""

        else:  # routine





















            draft = """Thank you for your email regarding "{subject}".
            
I've received your message and will respond appropriately.

Best regards"""

        return draft


# Cross-Account Categorization Views
class CategoryStatsView(APIView):
    """Get categorization statistics across all user accounts"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .services.categorization_engine import EmailCategorizationEngine

        engine = EmailCategorizationEngine(request.user)
        stats = engine.get_category_stats()

        return Response({"success": True, "stats": stats, "user_id": request.user.id})


class CrossAccountSyncView(APIView):
    """Trigger cross-account email synchronization"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .services.account_sync import CrossAccountSyncManager

        force_full_sync = request.data.get("force_full_sync", False)

        sync_manager = CrossAccountSyncManager(request.user)
        result = sync_manager.sync_all_accounts(force_full_sync)

        return Response(result)

    def get(self, request):
        """Get sync status for all accounts"""
        from .services.account_sync import CrossAccountSyncManager

        sync_manager = CrossAccountSyncManager(request.user)
        status = sync_manager.get_sync_status()

        return Response({"success": True, "sync_status": status})


class RecategorizeAccountView(APIView):
    """Recategorize emails for a specific account"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, account_id):
        from .services.account_sync import CrossAccountSyncManager

        category_filter = request.data.get("category_filter")

        sync_manager = CrossAccountSyncManager(request.user)
        result = sync_manager.recategorize_account_emails(account_id, category_filter)

        return Response(result)


class SmartCategorizationView(APIView):
    """Enhanced categorization endpoint with AI and real Gmail/Outlook integration"""

    permission_classes = [permissions.AllowAny]  # For extension compatibility

    def post(self, request):
        from .services.label_manager import process_email_triage
        from .services.openai_service import categorize_with_ai
        from rest_framework.exceptions import ParseError

        try:
            platform = request.data.get("platform", "gmail")
            emails = request.data.get("emails", [])
            single_email = request.data.get("email", {})
            action = request.data.get("action", "batch_triage")
            date_limit_days = request.data.get("date_limit_days", 7)
            user_email = request.data.get(
                "user_email", "user@example.com"
            )  # TODO: Get from auth
            user = request.user if request.user.is_authenticated else None

            logger.info(
                f"Triage request: {len(emails)} emails, platform: {platform}, action: {action}"
            )

            # Handle single email categorization with AI
            if action == "triage_single" and single_email:
                result = categorize_with_ai(single_email, user)

                return Response(
                    {
                        "success": True,
                        "category": result["category"],
                        "confidence": result["confidence"],
                        "priority": result["priority"],
                        "explanation": result["explanation"],
                        "email_id": single_email.get("id", "unknown"),
                        "platform": platform,
                        "ai_powered": result.get("ai_powered", False),
                    }
                )

            # Handle batch categorization with label application
            if emails and action == "batch_triage":
                # Limit batch size for performance
                max_batch_size = 50
                if len(emails) > max_batch_size:
                    logger.warning(
                        f"Batch size {len(emails)} exceeds limit, processing first {max_batch_size}"
                    )
                    emails = emails[:max_batch_size]

                # Filter emails by date if specified
                if date_limit_days:
                    from datetime import datetime, timedelta

                    cutoff_date = datetime.now() - timedelta(days=date_limit_days)
                    filtered_emails = []

                    for email in emails:
                        email_date = email.get("date")
                        if email_date:
                            try:
                                if isinstance(email_date, str):
                                    email_date = datetime.fromisoformat(
                                        email_date.replace("Z", "+00:00")
                                    )
                                if email_date >= cutoff_date:
                                    filtered_emails.append(email)
                            except Exception:
                                filtered_emails.append(
                                    email
                                )  # Include if date parsing fails
                        else:
                            filtered_emails.append(email)  # Include if no date

                    emails = filtered_emails
                    logger.info(
                        f"Filtered to {len(emails)} emails within {date_limit_days} days"
                    )

                # Process triage with real Gmail API integration
                triage_results = process_email_triage(user_email, emails, platform)

                return Response(
                    {
                        "success": triage_results["success"],
                        "processed": triage_results["processed"],
                        "total_emails": triage_results["total_emails"],
                        "categories": triage_results["categories"],
                        "label_applications": triage_results.get(
                            "label_applications", []
                        ),
                        "statistics": triage_results["statistics"],
                        "errors": triage_results.get("errors", []),
                        "platform": platform,
                        "date_limit_days": date_limit_days,
                        "timestamp": triage_results["timestamp"],
                    }
                )

            return Response(
                {"success": False, "error": "No emails provided for categorization"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ParseError as e:
            # Malformed JSON or bad request body
            logger.error(f"Triage request parse error: {e}")
            return Response(
                {"success": False, "error": "Invalid JSON payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Triage processing failed: {e}")
            return Response(
                {"success": False, "error": str(e), "platform": platform},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserLearningView(APIView):
    """Handle user feedback for learning"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .services.categorization_engine import EmailCategorizationEngine

        try:
            email_data = request.data.get("email_data", {})
            user_category = request.data.get("user_category")

            if not email_data or not user_category:
                return Response(
                    {
                        "success": False,
                        "error": "email_data and user_category are required",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            engine = EmailCategorizationEngine(request.user)
            engine.learn_from_user_action(email_data, user_category)

            return Response(
                {"success": True, "message": "Learning data updated successfully"}
            )

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class ExtensionHealthView(APIView):
    """Simple health check endpoint for extension connectivity testing"""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "message": "FYXERAI backend is running",
                "timestamp": timezone.now(),
                "extension_headers": {
                    "x-extension-source": request.headers.get(
                        "X-Extension-Source", "none"
                    ),
                    "origin": request.headers.get("Origin", "none"),
                },
            }
        )

    def head(self, request):
        return Response(status=status.HTTP_200_OK)

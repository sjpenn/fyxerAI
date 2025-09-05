from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_oauth

app_name = 'core'

# API URL patterns
api_urlpatterns = [
    # Health check
    path('health/', views.health_check, name='health-check'),
    
    # User management
    path('auth/register/', views.UserCreateView.as_view(), name='user-register'),
    path('auth/profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('auth/preferences/', views.UserPreferenceView.as_view(), name='user-preferences'),
    
    # Email accounts
    path('email-accounts/', views.EmailAccountListCreateView.as_view(), name='email-accounts'),
    path('email-accounts/<int:pk>/', views.EmailAccountDetailView.as_view(), name='email-account-detail'),
    
    # Email messages
    path('emails/', views.EmailMessageListView.as_view(), name='email-list'),
    path('emails/<int:pk>/', views.EmailMessageDetailView.as_view(), name='email-detail'),
    path('emails/<int:pk>/triage/', views.EmailMessageTriageView.as_view(), name='email-triage'),
    path('emails/reply/', views.EmailDraftGenerateView.as_view(), name='email-draft'),
    # Gmail direct message detail (on-demand)
    path('gmail/message/<str:message_id>/', views.gmail_message_detail, name='gmail-message-detail'),
    # Gmail list (metadata-first)
    path('gmail/messages/', views.gmail_message_list, name='gmail-message-list'),
    # Gmail Pub/Sub webhook
    path('gmail/webhook/', views.gmail_webhook, name='gmail-webhook'),
    
    # Cross-account categorization system
    path('categorization/stats/', views.CategoryStatsView.as_view(), name='category-stats'),
    path('categorization/sync/', views.CrossAccountSyncView.as_view(), name='cross-account-sync'),
    path('categorization/recategorize/<int:account_id>/', views.RecategorizeAccountView.as_view(), name='recategorize-account'),
    path('categorization/smart-triage/', views.SmartCategorizationView.as_view(), name='smart-categorization'),
    path('categorization/learn/', views.UserLearningView.as_view(), name='user-learning'),
    
    # Extension-compatible endpoints
    path('extension/health/', views.ExtensionHealthView.as_view(), name='extension-health'),
    path('extension/triage/', views.SmartCategorizationView.as_view(), name='extension-triage'),  # Updated to use smart categorization
    path('extension/reply/', views.ExtensionDraftView.as_view(), name='extension-reply'),
    
    # Meetings
    path('meetings/', views.MeetingListCreateView.as_view(), name='meeting-list'),
    path('meetings/<int:pk>/', views.MeetingDetailView.as_view(), name='meeting-detail'),
    path('meetings/<int:pk>/summary/', views.MeetingSummaryView.as_view(), name='meeting-summary'),
]

# HTMX partial URL patterns
htmx_urlpatterns = [
    path('email-inbox/', views.email_inbox_partial, name='email-inbox-partial'),
    path('email-accounts/', views.email_accounts_partial, name='email-accounts-partial'),
    path('email-stats/', views.email_stats_partial, name='email-stats-partial'),
    path('dashboard-overview/', views.dashboard_overview_partial, name='dashboard-overview-partial'),
    path('account-menu/', views.account_menu_partial, name='account-menu-partial'),
    path('gmail-inbox/', views.gmail_inbox_partial, name='gmail-inbox-partial'),
    path('gmail-message/<str:message_id>/', views.gmail_message_detail_partial, name='gmail-message-partial'),
]

# Main URL patterns (template views + API + HTMX)
urlpatterns = [
    # Template views
    path('', views.home, name='home'),
    path('components/', views.components_showcase, name='components'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    
    # Account menu helper (for nested sidebar)
    path('account-menu/', views.account_menu_partial, name='account_menu'),
    
    # OAuth authentication flows
    path('auth/gmail/login/', views_oauth.gmail_oauth_login, name='gmail_oauth_login'),
    path('auth/gmail/callback/', views_oauth.gmail_oauth_callback, name='gmail_oauth_callback'),
    path('auth/add-account/', views_oauth.add_account_form, name='add_account_form'),
    path('auth/disconnect/<int:account_id>/', views_oauth.disconnect_email_account, name='disconnect_account'),
    path('auth/debug/', views_oauth.oauth_debug_view, name='oauth_debug'),
    
    # HTMX partial views
    path('partials/', include(htmx_urlpatterns)),
    
    # API routes
    path('api/', include(api_urlpatterns)),
]

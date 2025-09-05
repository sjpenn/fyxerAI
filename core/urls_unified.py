"""
URL patterns for unified email processing views
"""

from django.urls import path
from . import views_unified

app_name = 'emails'

urlpatterns = [
    # Main dashboard
    path('dashboard/', views_unified.email_dashboard, name='dashboard'),
    
    # HTMX endpoints
    path('list/', views_unified.email_list, name='email_list'),
    path('<int:email_id>/detail/', views_unified.email_detail, name='email_detail'),
    path('stats/', views_unified.email_stats, name='email_stats'),
    
    # Email actions
    path('<int:email_id>/classify/', views_unified.classify_email, name='classify_email'),
    path('<int:email_id>/summarize/', views_unified.generate_summary, name='generate_summary'),
    path('<int:email_id>/draft/', views_unified.generate_draft, name='generate_draft'),
    
    # Account sync
    path('sync/gmail/', views_unified.sync_gmail, name='sync_gmail'),
    path('sync/outlook/', views_unified.sync_outlook, name='sync_outlook'),
    
    # Batch operations
    path('batch/', views_unified.process_batch, name='process_batch'),
]
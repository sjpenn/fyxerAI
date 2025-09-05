"""
Django views for unified email processing with HTMX
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache

from core.services.unified_email_service import (
    UnifiedEmailService,
    GmailIntegration,
    OutlookIntegration,
    EmailClassifier,
    EmailSummarizer
)
from core.models import EmailAccount, EmailMessage, UserPreference

import json
import sqlite3
from pathlib import Path


@login_required
def email_dashboard(request):
    """Main email dashboard with HTMX support."""
    service = UnifiedEmailService()
    stats = service.get_email_stats()
    
    # Get user's connected accounts
    accounts = EmailAccount.objects.filter(user=request.user)
    
    context = {
        'stats': stats,
        'accounts': accounts,
        'categories': EmailClassifier.DEFAULT_LABELS
    }
    
    return render(request, 'core/email_dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def email_list(request):
    """HTMX endpoint for email list with filtering."""
    category = request.GET.get('category', 'all')
    source = request.GET.get('source', 'all')
    page = int(request.GET.get('page', 1))
    per_page = 20
    
    service = UnifiedEmailService()
    
    # Build query
    query = "SELECT * FROM emails WHERE 1=1"
    params = []
    
    if source != 'all':
        query += " AND source = ?"
        params.append(source)
    
    if category != 'all':
        query += " AND categories LIKE ?"
        params.append(f'%"{category}"%')
    
    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])
    
    # Execute query
    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    columns = [desc[0] for desc in cursor.description]
    emails = []
    
    for row in cursor.fetchall():
        email = dict(zip(columns, row))
        # Parse JSON fields
        email['categories'] = json.loads(email['categories']) if email['categories'] else []
        email['labels'] = json.loads(email['labels']) if email['labels'] else []
        email['action_items'] = json.loads(email['action_items']) if email['action_items'] else []
        emails.append(email)
    
    conn.close()
    
    context = {
        'emails': emails,
        'category': category,
        'source': source,
        'page': page
    }
    
    return render(request, 'partials/email_list.html', context)


@login_required
@require_http_methods(["GET"])
def email_detail(request, email_id):
    """HTMX endpoint for email detail view."""
    service = UnifiedEmailService()
    
    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
    
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return HttpResponse("Email not found", status=404)
    
    email = dict(zip(columns, row))
    email['categories'] = json.loads(email['categories']) if email['categories'] else []
    email['action_items'] = json.loads(email['action_items']) if email['action_items'] else []
    
    # Generate draft if requested
    if request.GET.get('draft'):
        draft = service.generate_draft(email_id)
        email['draft_reply'] = draft
    
    return render(request, 'partials/email_detail.html', {'email': email})


@login_required
@require_http_methods(["POST"])
def sync_gmail(request):
    """HTMX endpoint to sync Gmail messages."""
    email_account = request.POST.get('account')
    query = request.POST.get('query', 'newer_than:7d')
    
    if not email_account:
        return HttpResponse("No account specified", status=400)
    
    service = UnifiedEmailService()
    
    try:
        # Check if authenticated
        gmail = GmailIntegration(email_account)
        
        if not gmail.service:
            # Not authenticated via API client; direct user to in-app OAuth
            from django.urls import reverse
            oauth_url = reverse('core:gmail_oauth_login')
            return HttpResponse(
                f'<div class="alert alert-warning">'
                f'Gmail authentication required. '
                f'<a href="{oauth_url}" target="_blank">Connect your Gmail</a>'
                f'</div>'
            )
        
        # Ingest emails
        count = service.ingest_gmail(email_account, query=query)
        
        # Auto-classify new emails
        service.classify_emails()
        
        return HttpResponse(
            f'<div class="alert alert-success">'
            f'Successfully synced {count} Gmail messages'
            f'</div>'
        )
        
    except Exception as e:
        return HttpResponse(
            f'<div class="alert alert-danger">'
            f'Error syncing Gmail: {str(e)}'
            f'</div>'
        )


@login_required
@require_http_methods(["POST"])
def sync_outlook(request):
    """HTMX endpoint to sync Outlook messages."""
    email_account = request.POST.get('account')
    
    if not email_account:
        return HttpResponse("No account specified", status=400)
    
    service = UnifiedEmailService()
    
    try:
        # Check if authenticated
        outlook = OutlookIntegration(email_account)
        
        if not outlook.token:
            # Need to authenticate
            flow = outlook.get_device_flow()
            
            # Store flow in session for callback
            request.session['outlook_flow'] = flow
            
            return HttpResponse(
                f'<div class="alert alert-warning">'
                f'Outlook authentication required.<br>'
                f'<strong>{flow["message"]}</strong>'
                f'</div>'
            )
        
        # Ingest emails
        count = service.ingest_outlook(email_account)
        
        # Auto-classify new emails
        service.classify_emails()
        
        return HttpResponse(
            f'<div class="alert alert-success">'
            f'Successfully synced {count} Outlook messages'
            f'</div>'
        )
        
    except Exception as e:
        return HttpResponse(
            f'<div class="alert alert-danger">'
            f'Error syncing Outlook: {str(e)}'
            f'</div>'
        )


@login_required
@require_http_methods(["POST"])
def classify_email(request, email_id):
    """HTMX endpoint to reclassify an email."""
    service = UnifiedEmailService()
    
    # Get email content
    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT subject, snippet, body_text FROM emails WHERE id = ?",
        (email_id,)
    )
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return HttpResponse("Email not found", status=404)
    
    subject, snippet, body = row
    
    # Classify
    text = f"{subject or ''}\n{snippet or ''}\n{body or ''}"
    categories = service.classifier.classify(text)
    
    # Update database
    cursor.execute(
        "UPDATE emails SET categories = ? WHERE id = ?",
        (json.dumps(categories), email_id)
    )
    conn.commit()
    conn.close()
    
    # Apply labels to source if requested
    if request.POST.get('apply_labels'):
        service.apply_labels_to_source(email_id)
    
    return HttpResponse(
        f'<div class="categories">'
        + ''.join([f'<span class="badge">{cat}</span>' for cat in categories])
        + '</div>'
    )


@login_required
@require_http_methods(["POST"])
def generate_summary(request, email_id):
    """HTMX endpoint to generate email summary."""
    service = UnifiedEmailService()
    
    # Get email content
    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT subject, body_text FROM emails WHERE id = ?",
        (email_id,)
    )
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return HttpResponse("Email not found", status=404)
    
    subject, body = row
    
    # Generate summary
    content = f"{subject or ''}\n{body or ''}"
    summary_data = service.summarizer.summarize(content)
    
    # Update database
    cursor.execute(
        "UPDATE emails SET summary = ?, action_items = ? WHERE id = ?",
        (summary_data['summary'], json.dumps(summary_data['action_items']), email_id)
    )
    conn.commit()
    conn.close()
    
    return render(request, 'partials/email_summary.html', {
        'summary': summary_data['summary'],
        'action_items': summary_data['action_items'],
        'key_points': summary_data.get('key_points', [])
    })


@login_required
@require_http_methods(["POST"])
def generate_draft(request, email_id):
    """HTMX endpoint to generate draft reply."""
    service = UnifiedEmailService()
    
    # Get user preferences
    preferences = UserPreference.objects.filter(user=request.user).first()
    tone = request.POST.get('tone', 'professional')
    
    # Generate draft
    draft = service.generate_draft(email_id)
    
    if not draft:
        return HttpResponse("Could not generate draft", status=500)
    
    # Store draft in session for editing
    request.session[f'draft_{email_id}'] = draft
    
    return render(request, 'partials/draft_reply.html', {
        'draft': draft,
        'email_id': email_id,
        'tone': tone
    })


@login_required
@require_http_methods(["POST"])
def process_batch(request):
    """HTMX endpoint for batch email processing."""
    action = request.POST.get('action')
    
    service = UnifiedEmailService()
    
    if action == 'classify':
        count = service.classify_emails(limit=100)
        message = f"Classified {count} emails"
    
    elif action == 'summarize':
        count = service.summarize_emails(limit=50)
        message = f"Summarized {count} emails"
    
    elif action == 'sync_all':
        # Sync all connected accounts
        total = 0
        accounts = EmailAccount.objects.filter(user=request.user)
        
        for account in accounts:
            if account.platform == 'gmail':
                total += service.ingest_gmail(account.email)
            elif account.platform == 'outlook':
                total += service.ingest_outlook(account.email)
        
        # Auto-classify
        service.classify_emails()
        message = f"Synced {total} emails from {accounts.count()} accounts"
    
    else:
        return HttpResponse("Unknown action", status=400)
    
    return HttpResponse(
        f'<div class="alert alert-success">{message}</div>'
    )


@login_required
def email_stats(request):
    """HTMX endpoint for email statistics."""
    service = UnifiedEmailService()
    stats = service.get_email_stats()
    
    return render(request, 'partials/email_stats.html', {'stats': stats})

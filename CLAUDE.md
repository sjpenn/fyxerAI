# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is FYXERAI-GEDS, an MVP AI-powered email assistant that replicates FyxerAI functionality. The system provides multi-account email triage, AI-drafted replies, meeting transcription/summarization, and unified dashboard management for Gmail and Outlook accounts.

## Tech Stack

### Backend
- **Framework**: Django 4.2 with HTMX for server-side rendering and partial updates
- **Database**: PostgreSQL (AWS RDS or Google Cloud SQL)
- **Storage**: AWS S3 for meeting transcripts and audio files
- **AI**: OpenAI API for draft generation and meeting summaries
- **APIs**: Google Workspace API, Microsoft Graph API, Zoom/Meet/Teams APIs

### Frontend
- **Templates**: Django templates enhanced with HTMX
- **JavaScript**: Alpine.js 3.x for lightweight interactivity
- **Styling**: Tailwind CSS 3.x with JIT mode enabled
- **Components**: ShadCN UI components adapted for Alpine.js
- **Build Tool**: Vite for asset compilation (development)

### Extensions & Add-ins
- **Browser Extensions**: Chrome/Edge Manifest v3 extensions
- **Outlook Add-in**: OfficeJS task pane add-in (manifest v1.1)

## Key Architecture Principles

### Django Project Structure
- Use Django 4.2 `path()` routing patterns, not deprecated `url()`
- Main project: `fyxerai_assistant/` with core app in `core/`
- Templates in `core/templates/` with HTMX-enabled partials
- Static files served from `static/` directory

### HTMX Integration
- All dynamic UI interactions via `hx-get`/`hx-post` attributes
- Return HTML partials for content swapping, not JSON
- Use `hx-target` and `hx-swap` for precise DOM updates
- No full page reloads for user interactions

### Alpine.js Usage
- Keep `x-data` state minimal and component-scoped
- Use Alpine stores (`Alpine.store()`) for global state (theme, user preferences)
- Embed JS logic within HTML templates, no external bundling
- Use event modifiers like `.debounce` for form interactions

### Tailwind CSS
- JIT mode enabled with purge paths: `templates/**/*.html`
- Use utility classes, avoid custom CSS overrides
- Dark theme as default with light mode toggle
- Component styling via `@apply` directives when needed

## Development Commands

### Django Development
```bash
# Start development server
python manage.py runserver

# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run tests
python manage.py test

# Run specific app tests
python manage.py test core
```

### Frontend Development
```bash
# Install dependencies
npm install

# Build Tailwind CSS
npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch

# Build for production
npm run build
```

### Extension Development
```bash
# Load Chrome extension for testing
# Navigate to chrome://extensions/ and load unpacked from /extension/

# Build Outlook add-in
cd outlook-addin && npm start
```

## Core Models & Database

### Key Models (in `core/models.py`)
- `EmailAccount`: OAuth-connected Gmail/Outlook accounts
- `EmailMessage`: Individual emails with categories and metadata
- `Meeting`: Meeting recordings and transcripts stored in S3
- `UserPreference`: User tone profiles and category settings

### OAuth Implementation
- Google OAuth: `/auth/google/login/` and `/auth/google/callback/`
- Microsoft OAuth: `/auth/outlook/login/` and `/auth/outlook/callback/`
- Store encrypted refresh tokens securely
- Validate `state` parameter in callbacks

## API Endpoints

### Core API Structure
```
/api/emails/              # GET: List categorized emails
/api/emails/reply/        # POST: Generate AI draft reply
/api/emails/triage/       # POST: Manually recategorize email
/api/meetings/summary/    # GET: Meeting summaries and follow-ups
/webhooks/zoom/           # POST: Zoom meeting webhook handler
```

### HTMX Endpoints
All API endpoints should return HTML partials for HTMX consumption, not JSON.

## AI Integration

### OpenAI Service (`/core/services/openai_service.py`)
- Implement `generate_reply(prompt, tone_profile)` for email drafts
- Use user's tone profile from past sent emails
- Implement retry/backoff for rate limits
- Cache frequent requests where appropriate

### Meeting Transcription
- Store audio files in S3 with encryption
- Use speech-to-text for transcription
- Generate structured meeting notes and action items

## Security Requirements

### OAuth Security
- Use HTTPS for all OAuth flows
- Encrypt stored refresh tokens (AES-256)
- Validate CSRF tokens on state changes
- Implement token refresh logic

### Data Protection
- TLS encryption for all external API calls
- Encrypt data at rest in database and S3
- Follow GDPR/HIPAA compliance patterns
- No sensitive data in logs or console output

## Browser Extension Architecture

### Manifest v3 Structure
```
/extension/
  ├── manifest.json          # Manifest v3 configuration
  ├── content.js            # Content script for Gmail/Outlook
  ├── background.js         # Service worker for API calls
  └── popup.html            # Extension popup interface
```

### Content Script Integration
- Inject category tags and draft buttons into Gmail/Outlook UI
- Use `chrome.runtime.sendMessage` for backend communication
- Maintain message namespaces to avoid conflicts

## Testing Strategy

### Backend Testing
```bash
# Run Django tests
python manage.py test

# Test specific functionality
python manage.py test core.tests.test_oauth
```

### Frontend Testing
- Use Vitest with JSDOM for Alpine component testing
- Cypress for end-to-end user flows
- Playwright for extension popup testing

### Integration Testing
- Test OAuth flows end-to-end
- Validate HTMX partial rendering
- Test extension-to-backend communication

## Deployment Configuration

### AWS Infrastructure
- RDS PostgreSQL 15.3 in us-east-1
- S3 bucket with encryption for transcripts
- Elastic Beanstalk for Django application hosting

### Environment Variables
```bash
DATABASE_URL=postgres://user:pass@host:5432/dbname
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET_NAME=...
```

## Key Development Rules

1. **No Full Page Reloads**: Use HTMX for all dynamic content updates
2. **Draft Only**: Never auto-send emails; always save to drafts folder first
3. **Multi-Account Support**: All models must support N:N user-account relationships
4. **Security First**: All OAuth tokens encrypted, all API calls over HTTPS
5. **Component Reusability**: Create reusable Alpine.js components in templates
6. **Performance**: Email classification <2sec, draft generation <5sec
7. **Accessibility**: Semantic HTML, ARIA attributes, keyboard navigation support

## Common Patterns

### HTMX Partial Update
```html
<div hx-get="/api/emails/triage/" hx-target="#inbox-panel" hx-swap="innerHTML">
  <!-- Email list content -->
</div>
```

### Alpine.js Component
```html
<div x-data="{ open: false, theme: $store.theme.current }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open" x-transition>Content</div>
</div>
```

### Django View for HTMX
```python
def triage_view(request):
    emails = EmailMessage.objects.filter(account__user=request.user)
    return render(request, 'partials/email_list.html', {'emails': emails})
```

This architecture ensures scalable, maintainable code that follows the project's core principles while maintaining security and performance standards.
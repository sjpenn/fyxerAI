# GEMINI.md

This file provides guidance to Gemini when working with code in this repository.

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

## Building and Running

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

## Development Conventions

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

### Security
- Use HTTPS for all OAuth flows
- Encrypt stored refresh tokens (AES-256)
- Validate CSRF tokens on state changes
- Implement token refresh logic
- TLS encryption for all external API calls
- Encrypt data at rest in database and S3
- Follow GDPR/HIPAA compliance patterns
- No sensitive data in logs or console output

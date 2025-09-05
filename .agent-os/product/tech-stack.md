# Technical Stack

## Application Framework
- **Framework:** Django 4.2
- **Language:** Python 3.11.4
- **Pattern:** Server-side rendering with HTMX for dynamic updates

## Database System
- **Primary Database:** PostgreSQL 15+ (AWS RDS or Google Cloud SQL)
- **ORM:** Django ORM
- **Migrations:** Django migrations system

## JavaScript Framework
- **Primary Framework:** Alpine.js 3.x
- **Pattern:** Progressive enhancement with declarative syntax
- **State Management:** Alpine stores for global state

## Import Strategy
- **Strategy:** Node.js modules via npm
- **Bundler:** Vite (development), Django staticfiles (production)
- **Module Loading:** ES6 imports

## CSS Framework
- **Framework:** Tailwind CSS 3.x
- **Mode:** JIT (Just-In-Time) compilation
- **Purge:** Configured for Django templates (`templates/**/*.html`)

## UI Component Library
- **Library:** ShadCN UI (adapted for Alpine.js)
- **Components:** Customized for Django template integration
- **Styling:** Tailwind-based with Alpine.js bindings

## Fonts Provider
- **Provider:** Google Fonts
- **Loading:** Self-hosted for performance
- **Primary Font:** Inter with sans-serif fallback

## Icon Library
- **Library:** Lucide icons
- **Integration:** Alpine.js compatible icon components
- **Format:** SVG icons for scalability

## Application Hosting
- **Platform:** AWS Elastic Beanstalk or AWS ECS/Fargate
- **Containerization:** Docker containers
- **Scaling:** Auto-scaling groups with load balancers

## Database Hosting
- **Service:** AWS RDS PostgreSQL
- **Region:** us-east-1 (primary)
- **Backup:** Daily automated backups with point-in-time recovery

## Asset Hosting
- **Storage:** AWS S3 for meeting transcripts and audio files
- **CDN:** CloudFront for static asset delivery
- **Access:** Presigned URLs for secure content access

## Deployment Solution
- **CI/CD:** GitHub Actions
- **Triggers:** Push to main/staging branches
- **Testing:** Automated test runs before deployment
- **Environments:** Staging and production branches

## Browser Extensions
- **Platform:** Chrome/Edge Manifest v3 extensions
- **Architecture:** Content scripts + service worker
- **Integration:** Native Gmail/Outlook interface overlay

## Outlook Add-in
- **Platform:** OfficeJS task pane add-in
- **Manifest:** Version 1.1 for web and desktop compatibility
- **Integration:** Outlook ribbon and compose integration

## AI Integration
- **Provider:** OpenAI API (GPT-4)
- **Services:** Draft generation, meeting summarization, email categorization
- **Optimization:** Token usage optimization and response caching

## External APIs
- **Email:** Google Workspace API, Microsoft Graph API
- **Calendar:** Google Calendar API, Outlook Calendar API
- **Meetings:** Zoom API, Google Meet API, Microsoft Teams API
- **Chat:** Slack API, Microsoft Teams API
- **CRM:** Salesforce API, HubSpot API

## Authentication
- **Method:** OAuth 2.0 for Google and Microsoft
- **Storage:** Encrypted refresh tokens with AES-256
- **Security:** TLS 1.2+ for all external communications

## Code Repository
- **Platform:** GitHub
- **URL:** https://github.com/[username]/fyxerai-geds
- **Branching:** GitFlow with main, staging, and feature branches
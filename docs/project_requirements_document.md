# Project Requirements Document

## 1. Project Overview

This project is an MVP “FyxerAI replica” that you’ll use as a personal AI executive assistant on top of your existing Gmail and Outlook inboxes. It connects via OAuth to your mail and calendar, automatically triages incoming messages into actionable categories (e.g., “To Respond,” “FYI,” “Marketing”), filters junk, and generates AI-drafted replies in your tone. Drafts land in your native Drafts folder for manual review—you stay in control and never have messages sent without your approval.

Beyond email, the assistant joins scheduled video meetings (Zoom, Google Meet, Teams), records and transcribes them, and then sends you structured meeting notes plus a follow-up draft. A unified web dashboard and browser/desktop add-ins let you manage multiple inboxes, adjust preferences, view analytics, and handle scheduling without leaving familiar interfaces. Success means instant triage for every new email, high-quality drafts ready in seconds, and meeting summaries that save you time.

## 2. In-Scope vs. Out-of-Scope

### In-Scope

*   Gmail and Outlook integration via OAuth (Google Workspace API, Microsoft Graph API)
*   Browser extension for Chrome/Edge and Outlook desktop add-in
*   Web dashboard (Django + HTMX) for unified inbox, calendar view, analytics, and settings
*   Automatic email classification into “To Respond,” “FYI,” “Marketing,” “Spam,” etc., with per-user learning
*   AI-drafted replies using OpenAI API, saved to user’s Drafts folder; manual review and send
*   On-demand draft generation via command palette or special forwarding address
*   Meeting bot for Zoom, Google Meet, Teams: recording, transcription (speech-to-text), summary, follow-up draft
*   Smart scheduling assistant that suggests meeting times and provides one-click booking links
*   User preferences: tone (formal/casual), category toggles, appearance (dark theme, accent color), integrations on/off
*   Single-user support now; architecture designed to scale to multiple users later
*   Data storage in AWS RDS (or Cloud SQL) and AWS S3 for transcripts; secure encryption in transit and at rest

### Out-of-Scope (Phase 1)

*   Native mobile app (iOS/Android)
*   Support for email providers beyond Gmail & Outlook
*   Advanced CRM integrations beyond HubSpot and Salesforce
*   Custom prompt editing or direct model selection (beyond tone presets)
*   Automatic sending of replies
*   Enterprise multi-tenant billing or team analytics beyond single-user metrics

## 3. User Flow

When a new user visits the web dashboard, they’re greeted by an onboarding wizard. First, they click **Connect Gmail** or **Connect Outlook**, triggering OAuth consent screens for mail, labels/folders, and calendar access. Next, they sample a few past sent emails to build a “tone profile.” Finally, they confirm permissions for meeting joins and transcript storage. Within 60 seconds, the assistant is live.

After setup, the user lands on a unified inbox view (combined or per-account). At the top are tabs for each inbox and category filters (“To Respond,” “FYI,” etc.). New emails auto-sort in real time. A draft icon appears on messages needing replies—clicking it shows an inline AI draft plus a **Send** button that pushes to the native mail service. A sidebar links to calendar summaries, meeting notes, analytics, and settings. In the calendar view, upcoming calls show a toggle to let the bot join; post-meeting, summaries and follow-up drafts appear in the inbox or a connected chat channel.

## 4. Core Features

*   **Multi-Account Email Integration**\
    OAuth-based connectors for Gmail & Outlook; unified inbox dashboard; provider-specific label/folder handling.
*   **Email Triage & Categorization**\
    ML classifier assigns “To Respond,” “FYI,” “Marketing,” “Spam,” user-definable categories; learns from manual recategorizations.
*   **AI-Drafted Replies**\
    OpenAI-powered drafts in user’s tone; context-aware (thread history, calendar/CRM data); drafts saved to Drafts folder; manual approval only.
*   **On-Demand Drafting**\
    Command palette or special forwarding address to request drafts for any message.
*   **Seamless Native Interface Integration**\
    Chrome/Edge extension and Outlook desktop add-in overlay category tags, action buttons, and draft indicators.
*   **Unified Web Dashboard**\
    Account management, category preferences, tone settings, analytics (messages sorted, time saved), billing links, and extension downloads.
*   **AI-Powered Meeting Notes & Follow-Ups**\
    Bot joins Zoom/Meet/Teams calls, records/transcribes, generates structured notes and action items, drafts follow-up email.
*   **Smart Scheduling Assistant**\
    Suggests meeting times based on availability/time zones, provides one-click booking links.
*   **Extensible Integrations**\
    Slack/MS Teams notifications, HubSpot/Salesforce CRM syncing, webhooks/REST API for task managers and ticketing systems.
*   **Security & Compliance**\
    Encrypted data storage (AES-256), TLS for all external calls, OAuth flows, ISO 27001 & SOC 2 patterns, GDPR/HIPAA controls.

## 5. Tech Stack & Tools

*   **Backend**: Django (Python), HTMX (HTML-over-the-wire), PostgreSQL (AWS RDS or Cloud SQL)
*   **Frontend**: Alpine.js (lightweight JS), Tailwind CSS, ShadCN UI components
*   **Browser Integrations**: Chrome & Edge extensions, Outlook add-in (OfficeJS)
*   **AI & APIs**: OpenAI API (GPT-4), Google Workspace API, Microsoft Graph API, Zoom/Google Meet/Teams APIs, Slack API, Salesforce & HubSpot APIs
*   **Storage**: AWS S3 (meeting transcripts, audio), RDS/Cloud SQL (metadata, configs)
*   **Dev Tools**: Cursor (AI-IDE), Claude Code (terminal assistant)
*   **Hosting**: AWS / GCP / Azure (Docker + Kubernetes or managed services)

## 6. Non-Functional Requirements

*   **Performance**:\
    – Email classification < 2 sec per message\
    – Draft generation < 5 sec (typical)\
    – Meeting summary delivered < 2 min post-call
*   **Scalability**:\
    Microservices with auto-scaling to handle spikes in classification, transcription, and draft requests
*   **Reliability**:\
    99.9% uptime, retry logic, circuit breakers, graceful degradation if external APIs fail
*   **Security & Compliance**:\
    OAuth for authentication, TLS 1.2+ for all traffic, AES-256 at rest, ISO 27001/SOC 2 controls, GDPR/HIPAA data handling
*   **Usability**:\
    Onboarding ≤ 60 sec, intuitive UI within existing inbox, keyboard shortcuts for power users

## 7. Constraints & Assumptions

*   Requires availability of Gmail & Outlook APIs and permissions to create labels/folders
*   OpenAI GPT-4 access (API keys) for LLM tasks
*   User provides consent to process past sent emails for tone profiling
*   Initial rollout is single-user; multi-user tenancy is planned but not implemented in MVP
*   Audio recording in meetings depends on host permissions and platform policies

## 8. Known Issues & Potential Pitfalls

*   **API Rate Limits**: Google/Microsoft may throttle requests—implement caching, backoff strategies, batch operations
*   **Label vs. Folder Differences**: Gmail labels can be multi-assigned; Outlook uses single folders—ensure mappings are clear to user
*   **LLM Hallucinations**: Drafts may contain inaccuracies—always require manual review and display source context
*   **Meeting Bot Restrictions**: Some platforms require host invite or passcode—provide manual override to upload recordings post-meeting
*   **Spam Misclassification**: Aggressive filtering might hide important mail—offer easy “show hidden” toggle and quick recategorization
*   **Data Privacy Concerns**: Users may worry about transcript storage—highlight encryption, local deletion options, and privacy settings

This document serves as the main brain for subsequent technical guides (Tech Stack Doc, Frontend Guidelines, Backend Structure, etc.) and leaves no ambiguity about the MVP’s scope, user flow, core features, tools, non-functional needs, assumptions, or risks.

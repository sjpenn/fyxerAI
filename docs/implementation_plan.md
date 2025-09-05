# Implementation plan

## Phase 1: Environment Setup

1. **Prevalidation**: In the project root, run `test -f manage.py || echo "No Django project detected"` to check if a Django project already exists. (Project Summary – Project Goal)

2. Install Python 3.11.4 exactly. (Tech Stack – Backend)
   - **Validation**: Run `python3 --version` and confirm output is `Python 3.11.4`.

3. Install Node.js v20.2.1 exactly. (Tech Stack – Dev Tools)
   - **Validation**: Run `node -v` and confirm output is `v20.2.1`.

4. Install AWS CLI v2 for deployment. (Tech Stack – Deployment)
   - **Validation**: Run `aws --version` and confirm it reports `aws-cli/2`.

5. Install and configure Cursor in the project. (Tech Stack – Dev Tools)
   a. Run `npm install -g @cursor/cli`.
   b. Create a file `cursor_metrics.md` in the project root. Refer to `cursor_project_rules.mdc` for guidance on populating this file. (Tech Stack – Dev Tools)

6. Create a Python virtual environment. (Tech Stack – Backend)
   - Command: `python3.11 -m venv .venv`
   - **Validation**: Run `source .venv/bin/activate` and confirm prompt changes.

7. Create a new Django project named `fyxerai_assistant`. (Project Summary – Core Features)
   - Command: `django-admin startproject fyxerai_assistant .`
   - **Validation**: Confirm presence of `manage.py` and `fyxerai_assistant/settings.py`.

8. Create a Django app named `core`. (PRD Section: Multi-Account Integration)
   - Command: `python manage.py startapp core`
   - **Validation**: Confirm presence of `core/models.py`.

9. Initialize Git repository and create `.gitignore`. (PRD Section: Security and Privacy)
   - Include `.venv/`, `cursor_metrics.md`, `node_modules/`, and `.env`.
   - **Validation**: Run `git status` to ensure ignored files are not shown.

10. Initialize Node project for browser extension and dashboard tooling. (Project Summary – Browser Integrations)
    - Command: `npm init -y` in project root.
    - **Validation**: Confirm `package.json` exists.

## Phase 2: Frontend Development

11. Install Tailwind CSS v3 and Alpine.js. (Tech Stack – Frontend)
    - Run `npm install tailwindcss@3 postcss@8 autoprefixer@10 alpinejs@3`
    - **Validation**: Confirm dependencies in `package.json`.

12. Generate Tailwind config file at `/tailwind.config.cjs`. (Tech Stack – Frontend)
    - Command: `npx tailwindcss init -p`
    - **Validation**: Confirm `tailwind.config.cjs` and `postcss.config.cjs` exist.

13. Configure Tailwind to scan Django templates. (App Flow – UI Design)
    - In `/tailwind.config.cjs`, set `content: ['./**/templates/**/*.html']`.

14. Install ShadCN UI components. (Tech Stack – Frontend)
    - Run `npm install @shadcn/ui`
    - **Validation**: Confirm importable modules in `node_modules/@shadcn/ui`.

15. Create a base Django template at `/core/templates/base.html`. (UI Design)
    ```html
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>FYXERAI Dashboard</title>
      <script src="/static/alpine.js"></script>
      <link href="/static/css/tailwind.css" rel="stylesheet">
    </head>
    <body class="bg-gray-900 text-gray-100 font-inter">
      {% block content %}{% endblock %}
    </body>
    </html>
    ```
    - **Validation**: Load `http://localhost:8000/` and confirm blank page with correct CSS.

16. Configure Django static files for Tailwind and Alpine. (Tech Stack – Backend)
    - In `settings.py`, set `STATIC_URL = '/static/'` and `STATICFILES_DIRS = [BASE_DIR / 'static']`.
    - **Validation**: Run `python manage.py collectstatic --noinput` without errors.

17. Create a dashboard home view in `/core/views.py`. (App Flow – Unified Dashboard)
    ```python
    from django.shortcuts import render
    def home(request):
        return render(request, 'dashboard.html')
    ```
    - Map to path in `/fyxerai_assistant/urls.py`.
    - **Validation**: Visiting `/` returns the base template.

18. Create `/core/templates/dashboard.html` with placeholder cards for email accounts. (UI Design)
    - Use ShadCN UI card components.
    - **Validation**: Reload `/` and confirm cards render.

19. Implement Alpine.js component for dynamic theme toggle (light/dark). (UI Design)
    - Add `<script>` in `base.html` to toggle `classList` on `<body>`.
    - **Validation**: Click toggle and confirm theme changes.

20. Scaffold browser extension manifest at `/extension/manifest.json`. (Project Summary – Browser Integrations)
    ```json
    {
      "manifest_version": 3,
      "name": "FYXERAI Assistant",
      "version": "0.1.0",
      "content_scripts": [
        {
          "matches": ["https://mail.google.com/*","https://outlook.live.com/*"],
          "js": ["content.js"]
        }
      ]
    }
    ```
    - **Validation**: Load unpacked extension in Chrome and confirm it appears.

21. Create `/extension/content.js` with a placeholder console log. (Project Summary – Browser Integrations)
    ```js
    console.log('FYXERAI content script loaded');
    ```
    - **Validation**: Open Gmail and check console message.

22. Set up Outlook add-in project at `/outlook-addin/manifest.xml` using OfficeJS. (Project Summary – Browser Integrations)
    - Use Office Add-in Yeoman generator: `yo office --projectType taskpane --name fyxeraiAddin --host Outlook`
    - **Validation**: Run `npm start` in `/outlook-addin` and sideload in Outlook Web.

## Phase 3: Backend Development

23. Configure PostgreSQL connection for AWS RDS. (Tech Stack – Database)
    - In `.env`, set `DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME`
    - In `settings.py`, use `dj-database-url` to parse `DATABASE_URL`.
    - **Validation**: Run `python manage.py migrate` successfully.

24. Install required Python packages. (Tech Stack – Backend)
    - Run `pip install django==4.2.9 psycopg2-binary django-environ openai python-dotenv requests`
    - **Validation**: Confirm in `pip freeze`.

25. Define database schema in `/core/models.py`. (PRD Section: Data Storage)
    ```python
    class EmailAccount(models.Model):
        user = models.ForeignKey(User, on_delete=models.CASCADE)
        provider = models.CharField(max_length=20)  # gmail or outlook
        oauth_token = models.TextField()

    class EmailMessage(models.Model):
        account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE)
        message_id = models.CharField(max_length=255, unique=True)
        category = models.CharField(max_length=50)
    ```
    - **Validation**: Run `python manage.py makemigrations` and `migrate`.

26. Implement OAuth flow for Google in `/core/views.py`. (Project Summary – Key External Services)
    - Add view `/auth/google/login/` and callback `/auth/google/callback/` using `google-auth`.
    - **Validation**: Authenticate and confirm database entry in `EmailAccount`.

27. Implement OAuth flow for Outlook in `/core/views.py`. (Project Summary – Key External Services)
    - Add view `/auth/outlook/login/` and callback `/auth/outlook/callback/` using `msal`.
    - **Validation**: Authenticate and confirm database entry in `EmailAccount`.

28. Create API endpoint `GET /api/emails/` in `/core/urls.py`. (PRD Section: Email Categorization)
    - Implement view returning JSON list of `EmailMessage` objects for the logged-in user.
    - **Validation**: Use `curl` to fetch `/api/emails/` and confirm 200 response with JSON.

29. Configure CORS for frontend and extensions in `settings.py`. (App Flow – Integration)
    - Install `django-cors-headers` and add `CORS_ALLOWED_ORIGINS = ['http://localhost:8000']` and extension origins.
    - **Validation**: Test API call from extension content script via `fetch`.

30. Integrate OpenAI API for draft generation. (Project Summary – AI & APIs)
    - In `/core/services/openai_service.py`, implement `generate_reply(prompt)` using `openai.ChatCompletion.create(...)`.
    - **Validation**: Run a management command `python manage.py generate_test_reply` and confirm output.

31. Implement ML-based categorization worker in `/core/tasks.py`. (PRD Section: Email Categorization)
    - Schedule via `django-crontab` every 5 minutes to categorize new emails.
    - **Validation**: Confirm new `category` values appear in `EmailMessage` records.

32. Configure meeting transcription storage. (Project Summary – Storage)
    - Install `boto3` and configure AWS credentials in `.env`.
    - Create `/core/services/s3_client.py` with `upload_transcript(file_obj)`.
    - **Validation**: Upload a dummy text file and confirm presence in the S3 bucket.

33. Create model and migration for meetings in `/core/models.py`. (Project Summary – Meeting notes)
    ```python
    class Meeting(models.Model):
        account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE)
        transcript_s3_key = models.CharField(max_length=255)
        summary = models.TextField()
    ```
    - **Validation**: `makemigrations` & `migrate`.

34. Integrate Zoom/Google Meet/Teams APIs for transcript retrieval. (Project Summary – Key External Services)
    - In `/core/services/meeting_service.py`, implement `fetch_transcript(meeting_id)`.
    - **Validation**: Mock call and confirm transcript storage.

35. Add user preferences model in `/core/models.py` for categories and tone. (Project Summary – User Settings)
    ```python
    class UserPreference(models.Model):
        user = models.OneToOneField(User, on_delete=models.CASCADE)
        categories = JSONField(default=list)
        tone_profile = JSONField(default=dict)
    ```
    - **Validation**: CRUD via Django admin.

## Phase 4: Integration

36. Connect dashboard components to backend via HTMX. (Tech Stack – Frontend)
    - Replace placeholder cards with `<div hx-get="/api/emails/" hx-trigger="load"></div>`.
    - **Validation**: Dashboard shows email JSON when loaded.

37. Implement email reply UI in `/core/templates/reply_modal.html`. (PRD Section: AI-Powered Draft Replies)
    - Use ShadCN modal component and Alpine to handle text editing.
    - **Validation**: Open modal and confirm text area is editable.

38. Wire modal submit to `/api/emails/reply/` endpoint. (PRD Section: AI-Powered Draft Replies)
    - In `/core/views.py`, add `@csrf_exempt` view that calls `openai_service.generate_reply`.
    - **Validation**: Submit test prompt and confirm draft stored in `EmailMessage.draft`.

39. Extend browser extension to inject a “Generate Reply” button in Gmail UI. (Project Summary – Browser Integrations)
    - In `/extension/content.js`, use DOM selectors to place button near reply area.
    - **Validation**: Gmail shows button and clicking it triggers a console log.

40. Implement extension-background script in `/extension/background.js` to call backend. (Project Summary – Browser Integrations)
    ```js
    chrome.runtime.onMessage.addListener((msg, sender) => {
      fetch('http://localhost:8000/api/emails/reply/', { method: 'POST', body: JSON.stringify({text: msg.emailBody}) })
        .then(res => res.json()).then(d => console.log(d));
    });
    ```
    - **Validation**: Clicking extension button logs AI draft in console.

41. Add Slack integration for notifications in `/core/services/slack_service.py`. (Project Summary – Integrations)
    - Implement `send_notification(channel, text)` using `slack_sdk`.
    - **Validation**: Run `python manage.py send_test_slack` and confirm message in Slack.

42. Integrate CRM APIs (Salesforce & HubSpot). (Project Summary – Integrations)
    - Create `/core/services/crm_service.py` with stub functions `sync_contact(email)`.
    - **Validation**: Run management command `python manage.py sync_test_crm` without errors.

## Phase 5: Deployment

43. Add Terraform configuration in `/infra/terraform` for AWS RDS (PostgreSQL 15.3) in `us-east-1`. (Tech Stack – Deployment)
    - Define `aws_db_instance` with engine `postgres`, version `15.3`.
    - **Validation**: `terraform plan` shows creation of RDS instance.

44. Add Terraform `aws_s3_bucket` for meeting transcripts in `us-east-1`. (Project Summary – Storage)
    - Define bucket with encryption enabled.
    - **Validation**: `terraform apply` and confirm bucket exists.

45. Create GitHub Actions CI workflow in `/ .github/workflows/ci.yml`. (Project Summary – Dev Tools)
    - Steps: checkout, set up Python 3.11, install deps, run `pytest` and `npm test`.
    - **Validation**: Push commit and confirm green CI.

46. Provision AWS Elastic Beanstalk application for Django in `us-east-1`. (Tech Stack – Deployment)
    - Add EB config file `/infra/beanstalk/Dockerfile`.
    - **Validation**: Deploy and confirm health status `Ok`.

47. Deploy browser extension as Chrome Web Store draft. (Project Summary – Browser Integrations)
    - Use `chrome-webstore-upload` CLI to upload version `0.1.0`.

48. Deploy Outlook add-in to an Azure App Service. (Project Summary – Browser Integrations)
    - Push `/outlook-addin` to Azure and confirm manifest reachable via HTTPS.

49. Run end-to-end tests using Cypress in `/frontend/cypress`. (Q&A: Pre-Launch Checklist)
    - **Validation**: All tests pass against staging URL.

50. Conduct security audit: run `bandit .` for Python and `npm audit`. (Q&A: Security)
    - **Validation**: Zero critical vulnerabilities.

---

*All steps are sequenced to ensure reproducible environment setup, development, integration, and deployment.*
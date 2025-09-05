# FYXERAI Outlook Add-in

AI-powered email assistant for Microsoft Outlook desktop application.

## Features

- **AI Email Triage**: Automatically categorize emails as Urgent, Important, Routine, or Spam
- **Smart Draft Generation**: Generate AI-powered email drafts based on context
- **Real-time Backend Integration**: Connect to FYXERAI Django backend for processing
- **Outlook Integration**: Native buttons in Outlook ribbon and task pane interface

## Installation

### Prerequisites

- Microsoft Outlook (Desktop version)
- Node.js 16+ installed
- FYXERAI Django backend running on `http://localhost:8002`

### Development Setup

1. Install dependencies:
```bash
cd outlook-addin
npm install
```

2. Generate development certificates:
```bash
npm run start
```

3. Sideload the add-in in Outlook:
```bash
npm run sideload
```

### Manual Installation

1. In Outlook, go to **File > Options > Add-ins**
2. Select **Manage: COM Add-ins** and click **Go...**
3. Click **Developer Add-ins** and browse to `manifest.xml`
4. The FYXERAI add-in should appear in your Outlook ribbon

## Usage

### Task Pane

1. Click the **FYXERAI** button in the Outlook ribbon
2. The task pane will open showing connection status
3. Select an email and click **Triage Email** to categorize
4. Click **Generate AI Draft** to create a smart reply

### Quick Actions

- **Triage Email**: Click the triage button in the ribbon to quickly categorize the selected email
- **AI Draft**: Click the AI draft button to generate a reply directly

## API Integration

The add-in connects to the FYXERAI Django backend at:
- **Base URL**: `http://localhost:8002`
- **Triage Endpoint**: `/api/emails/triage/`
- **Reply Endpoint**: `/api/emails/reply/`

## File Structure

```
outlook-addin/
├── manifest.xml          # Add-in manifest for Outlook
├── taskpane.html         # Main task pane interface
├── commands.html         # UI-less command functions
├── package.json          # Node.js dependencies
├── webpack.config.js     # Build configuration
└── README.md            # This file
```

## Security

- All communications use HTTPS in production
- API calls include `X-Outlook-Addin` headers for identification
- No sensitive data is stored locally in the add-in

## Troubleshooting

### Connection Issues

1. Ensure Django backend is running on port 8002
2. Check that CORS is properly configured in Django settings
3. Verify the add-in has internet connectivity

### Add-in Not Loading

1. Clear Outlook cache: `%appdata%/Microsoft/Outlook`
2. Restart Outlook completely
3. Re-sideload the add-in using `npm run sideload`

### Development

For development with hot reload:
```bash
npm run dev-server
```

This starts a webpack dev server on `https://localhost:3000` with automatic reloading.

## Support

For issues or questions:
- Check Django backend logs for API errors
- Use Outlook Developer Tools (F12 when add-in is open)
- Review browser console for JavaScript errors
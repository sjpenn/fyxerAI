# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-08-19-django-postgresql-setup/spec.md

## API Endpoints

### GET /admin/
**Purpose:** Django admin interface for development and data management
**Parameters:** None (requires admin authentication)
**Response:** HTML admin interface
**Errors:** 
- 403 Forbidden - User not authenticated as admin
- 404 Not Found - Admin URLs not configured

### GET /api/health/
**Purpose:** Health check endpoint for deployment verification and monitoring
**Parameters:** None
**Response:** JSON health status with database connectivity check
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-08-19T10:30:00Z"
}
```
**Errors:**
- 500 Internal Server Error - Database connection failed
- 503 Service Unavailable - Application not ready

### GET /api/users/me/
**Purpose:** Get current authenticated user information for frontend initialization
**Parameters:** Authentication token required
**Response:** User profile data
```json
{
  "id": 1,
  "username": "user@example.com",
  "email": "user@example.com",
  "timezone": "America/New_York",
  "created_at": "2025-08-19T09:00:00Z"
}
```
**Errors:**
- 401 Unauthorized - Authentication token missing or invalid
- 404 Not Found - User not found

### GET /api/email-accounts/
**Purpose:** List all email accounts for authenticated user
**Parameters:** Authentication token required
**Response:** Array of email account objects
```json
{
  "results": [
    {
      "id": 1,
      "provider": "gmail",
      "email_address": "user@gmail.com",
      "display_name": "John Doe",
      "is_active": true,
      "created_at": "2025-08-19T09:00:00Z"
    }
  ],
  "count": 1
}
```
**Errors:**
- 401 Unauthorized - Authentication token missing or invalid

### POST /api/email-accounts/
**Purpose:** Create new email account connection (OAuth integration placeholder)
**Parameters:** Provider and OAuth callback data
```json
{
  "provider": "gmail",
  "email_address": "user@gmail.com",
  "display_name": "John Doe",
  "access_token": "...",
  "refresh_token": "...",
  "provider_user_id": "12345"
}
```
**Response:** Created email account object
**Errors:**
- 400 Bad Request - Invalid provider or missing required fields
- 401 Unauthorized - Authentication token missing or invalid
- 409 Conflict - Email account already exists

### GET /api/email-accounts/{id}/
**Purpose:** Get specific email account details
**Parameters:** Account ID in URL path
**Response:** Email account object (without sensitive token data)
**Errors:**
- 401 Unauthorized - Authentication token missing or invalid
- 403 Forbidden - Account belongs to different user
- 404 Not Found - Account not found

### DELETE /api/email-accounts/{id}/
**Purpose:** Remove email account connection
**Parameters:** Account ID in URL path
**Response:** 204 No Content on success
**Errors:**
- 401 Unauthorized - Authentication token missing or invalid
- 403 Forbidden - Account belongs to different user
- 404 Not Found - Account not found

### GET /api/preferences/
**Purpose:** Get user preferences for frontend initialization
**Parameters:** Authentication token required
**Response:** User preference object
```json
{
  "tone_profile": {},
  "enabled_categories": ["to_respond", "fyi", "marketing", "spam"],
  "theme": "dark",
  "timezone": "America/New_York",
  "slack_notifications": false,
  "teams_notifications": false
}
```
**Errors:**
- 401 Unauthorized - Authentication token missing or invalid

### PUT /api/preferences/
**Purpose:** Update user preferences
**Parameters:** Preference update object
**Response:** Updated preference object
**Errors:**
- 400 Bad Request - Invalid preference data
- 401 Unauthorized - Authentication token missing or invalid

## Controllers and Business Logic

### HealthCheckView
- **Action:** `get`
- **Business Logic:** Check database connectivity, return system status
- **Error Handling:** Catch database errors and return appropriate HTTP status

### UserProfileView
- **Action:** `get`
- **Business Logic:** Return authenticated user data excluding sensitive fields
- **Error Handling:** Handle authentication failures and user lookup errors

### EmailAccountViewSet
- **Actions:** `list`, `create`, `retrieve`, `destroy`
- **Business Logic:** 
  - Filter accounts by authenticated user
  - Encrypt OAuth tokens before database storage
  - Validate provider-specific requirements
- **Error Handling:** OAuth validation, duplicate account prevention, permission checks

### UserPreferenceView
- **Actions:** `get`, `update`
- **Business Logic:**
  - Create preferences on first access if not exists
  - Validate JSON structure for complex fields
  - Apply preference defaults
- **Error Handling:** JSON validation, preference constraint checking

## Authentication and Authorization

### Authentication Method
- Django's built-in session authentication for development phase
- Token-based authentication preparation for future API expansion
- CSRF protection for all non-GET requests

### Permission Classes
- `IsAuthenticated` for all API endpoints except health check
- Custom permission for email account ownership verification
- Admin-only access for Django admin interface

## API Design Patterns

### RESTful Conventions
- Standard HTTP methods (GET, POST, PUT, DELETE)
- Resource-based URL structure (/api/resource/ and /api/resource/{id}/)
- Consistent JSON response format with error handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email address format",
    "details": {
      "field": "email_address",
      "value": "invalid-email"
    }
  }
}
```

### Pagination
- Django Rest Framework pagination for list endpoints
- Page size limits to prevent performance issues
- Next/previous page links in response metadata

## Development and Testing Endpoints

### GET /api/dev/reset-db/
**Purpose:** Development-only endpoint to reset database with sample data
**Parameters:** Only available in DEBUG mode
**Response:** Success message with sample data summary
**Errors:** 
- 404 Not Found - Not available in production
- 500 Internal Server Error - Database reset failed
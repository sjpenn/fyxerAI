# Technical Specification: Phase 2 Frontend Setup

## Architecture Overview

### Frontend Stack Architecture
```
┌─────────────────────────────────────────┐
│             Browser Layer               │
├─────────────────────────────────────────┤
│ Alpine.js Components │ Chrome Extension │
├─────────────────────────────────────────┤
│           Django Templates              │
├─────────────────────────────────────────┤
│ Tailwind CSS │ ShadCN UI │ Static Files │
├─────────────────────────────────────────┤
│            Django Backend               │
└─────────────────────────────────────────┘
```

## Technical Requirements

### CSS Framework (Tailwind CSS v3)
- **Version**: Tailwind CSS 3.x with JIT (Just-In-Time) compilation
- **Configuration**: Custom `tailwind.config.cjs` with Django template scanning
- **Build Tool**: PostCSS with Autoprefixer for vendor prefixes
- **Custom Tokens**: Design system tokens for colors, typography, spacing
- **Bundle Size**: Target <200KB CSS bundle in production
- **Performance**: Sub-2s rebuild times during development

### JavaScript Framework (Alpine.js v3)
- **Version**: Alpine.js 3.x for reactive components
- **Bundle**: CDN or local bundle (prefer local for offline development)
- **State Management**: Alpine stores for global state (theme, user preferences)
- **Component Pattern**: x-data for local state, x-show/x-if for conditionals
- **Event Handling**: Alpine event modifiers for debouncing and key handling
- **Performance**: Zero virtual DOM overhead, direct DOM manipulation

### UI Component Library (ShadCN UI)
- **Adaptation**: ShadCN UI components adapted for Alpine.js (originally React)
- **Components**: Button, Card, Modal, Input, Toggle, Badge, Avatar components
- **Theming**: CSS variable-based theming for dark/light mode support
- **Accessibility**: ARIA attributes and keyboard navigation included
- **Customization**: Tailwind utility classes for component variants

### Django Integration
- **Static Files**: `STATIC_URL = '/static/'` with `STATICFILES_DIRS` configuration
- **Template Engine**: Django template system with `APP_DIRS = True`
- **CSRF**: Cross-Site Request Forgery protection enabled for forms
- **Debug**: Development server static file serving enabled
- **Compression**: Django-compressor for production asset optimization (future)

## Dependencies

### Node.js Dependencies
```json
{
  "tailwindcss": "^3.0.0",
  "postcss": "^8.0.0", 
  "autoprefixer": "^10.0.0",
  "alpinejs": "^3.0.0",
  "@shadcn/ui": "latest"
}
```

### Python Dependencies
```python
# Already installed in Phase 1
django==4.2.9
```

### Build Dependencies
- **Node.js**: v20.2.1 (from implementation plan, current v23.11.0 acceptable)
- **npm**: Latest version for package management
- **PostCSS CLI**: For CSS processing and build scripts

## File Structure

### Frontend Asset Organization
```
fyxerAI-GEDS/
├── static/
│   ├── css/
│   │   ├── input.css        # Tailwind source
│   │   └── output.css       # Compiled CSS
│   ├── js/
│   │   ├── alpine.js        # Alpine.js library
│   │   └── components/      # Custom Alpine components
│   └── components/          # ShadCN UI components
├── core/templates/
│   ├── base.html           # Base template
│   ├── dashboard.html      # Dashboard layout
│   └── partials/           # Reusable template parts
├── extension/
│   ├── manifest.json       # Chrome extension manifest
│   ├── content.js          # Content script
│   ├── popup.html          # Extension popup
│   └── background.js       # Service worker
├── tailwind.config.cjs     # Tailwind configuration
├── postcss.config.cjs      # PostCSS configuration
└── package.json            # Node.js dependencies
```

### Template Inheritance Structure
```
base.html
├── dashboard.html
├── auth/
│   ├── login.html
│   └── signup.html
└── partials/
    ├── navbar.html
    ├── sidebar.html
    └── theme-toggle.html
```

## Configuration Details

### Tailwind Configuration (`tailwind.config.cjs`)
```javascript
module.exports = {
  content: [
    './core/templates/**/*.html',
    './static/js/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {...},
        secondary: {...}
      }
    }
  },
  plugins: []
}
```

### Django Settings Updates
```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps
    'core',
]

# Static files configuration
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Template configuration (already configured)
TEMPLATES = [{
    'DIRS': [],  # Uses APP_DIRS for core/templates/
    'APP_DIRS': True,
    # ...
}]
```

## Browser Extension Technical Specs

### Manifest v3 Configuration
```json
{
  "manifest_version": 3,
  "name": "FYXERAI Assistant",
  "version": "0.1.0",
  "permissions": ["activeTab"],
  "content_scripts": [{
    "matches": [
      "https://mail.google.com/*",
      "https://outlook.live.com/*"
    ],
    "js": ["content.js"]
  }],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html"
  }
}
```

### Content Script Architecture
- **DOM Injection**: Non-invasive UI element injection
- **Message Passing**: chrome.runtime.sendMessage for backend communication
- **CSS Isolation**: Shadow DOM or scoped CSS to avoid conflicts
- **Event Handling**: Click handlers for FYXERAI-specific buttons

## Performance Requirements

### Build Performance
- **CSS Compilation**: <2 seconds for full Tailwind rebuild
- **Template Rendering**: <100ms for dashboard template
- **Static File Serving**: <50ms response time in development
- **Extension Loading**: <1 second initialization time

### Runtime Performance
- **Page Load**: <3 seconds initial dashboard load (3G connection)
- **Theme Toggle**: <100ms visual feedback
- **Alpine.js Initialization**: <500ms component ready state
- **Memory Usage**: <50MB JavaScript heap size

### Browser Compatibility
- **Minimum Versions**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Feature Detection**: Graceful degradation for older browsers
- **Polyfills**: None required for target browser versions
- **CSS Grid/Flexbox**: Full support assumed

## Security Considerations

### Content Security Policy (CSP)
```http
Content-Security-Policy: 
  default-src 'self';
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
```

### Extension Security
- **Permissions**: Minimal permissions (activeTab only)
- **HTTPS**: All external communications over HTTPS
- **Input Sanitization**: HTML escaping for dynamic content
- **Cross-Origin**: Proper CORS configuration for backend communication

## Testing Strategy

### Unit Testing
- **Alpine.js Components**: Component behavior and state management
- **Tailwind CSS**: Class generation and purging verification
- **Django Templates**: Template rendering and context passing

### Integration Testing
- **Theme Switching**: Dark/light mode persistence and application
- **Extension Integration**: Content script injection and communication
- **Responsive Design**: Multiple viewport testing

### Browser Testing
- **Cross-Browser**: Automated testing in Chrome, Firefox, Safari, Edge
- **Mobile Testing**: iOS Safari and Chrome Mobile verification
- **Extension Testing**: Chrome extension developer mode validation

## Error Handling

### Frontend Error Boundaries
- **Alpine.js Errors**: Component-level error handling with fallbacks
- **CSS Loading**: Graceful degradation when stylesheets fail
- **Extension Errors**: Silent failure with console logging only

### Development Debugging
- **Source Maps**: Enabled for CSS and JS debugging
- **Console Logging**: Structured logging for development
- **Hot Reload**: File watching for automatic browser refresh
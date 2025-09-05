# Frontend Guideline Document

This document lays out the frontend architecture, design principles, and technologies for our AI-powered email assistant project. It covers both the unified web dashboard and the browser/Outlook extension interfaces. Anyone should be able to understand how our frontend is built, styled, and maintained.

## 1. Frontend Architecture

### 1.1 Overall Structure
- **Two frontends**:
  - **Unified Web Dashboard**: A Django-served app enhanced with HTMX for server-driven interactivity and Alpine.js for local behavior.
  - **Browser/Outlook Extension**: A Manifest V3 extension (Chrome/Edge) and an OfficeJS add-in for Outlook desktop, built as static assets with Alpine.js.

### 1.2 Frameworks and Libraries
- **Django Templates + HTMX**: Server renders HTML; HTMX swaps fragments for dynamic updates without a full page reload.
- **Alpine.js**: Small, declarative JavaScript for dropdowns, modals, tabs, form interactions.
- **Tailwind CSS**: Utility-first styling, configured via PostCSS.
- **ShadCN UI**: A set of prebuilt, accessible components (adapted for Alpine) to speed up common UI patterns.
- **Vite**: Fast bundler for compiling and hot-reloading assets in development; produces optimized bundles for production.

### 1.3 Scalability, Maintainability, Performance
- **Component-based**: Logical grouping of HTML/CSS/JS into reusable units.
- **Server-driven UI with HTMX**: Reduces heavy client-side frameworks, offloads logic to backend, simplifies state.
- **Shared asset pipeline**: Single Vite config for both dashboard and extension, ensuring consistency and predictable builds.
- **Code splitting & lazy loading**: Only load JS modules and CSS when needed.

## 2. Design Principles

1. **Usability**: Clear labels, minimal clicks, familiar patterns (e.g., Gmail/Outlook styling).
2. **Accessibility (a11y)**: Semantic HTML, ARIA attributes, keyboard navigation, sufficient color contrast.
3. **Responsiveness**: Mobile-first design; fluid layouts adapt to screen size (dashboard) or extension pop-up.
4. **Consistency**: Uniform look and behavior across web dashboard and in-inbox UI.
5. **Performance**: Instant feedback on interactions; sub-second responses where possible.

### Applying Principles
- Buttons and links use clear text labels.
- All form fields have associated `<label>` tags.
- Dark mode by default, with a toggle for light mode.
- Consistent spacing, typography, and iconography guided by our design system (ShadCN UI).

## 3. Styling and Theming

### 3.1 Styling Approach
- **Utility-first (Tailwind CSS)**: Rapid styling via classes (e.g., `p-4`, `text-gray-200`).
- **Custom CSS (BEM-inspired)**: Rare for global overrides or third-party overrides, using a light BEM convention (`.fx-alert`, `.fx-alert--error`).
- **PostCSS**: Processes Tailwind directives, autoprefixing.

### 3.2 Theming
- **Dark theme (default)**: Most users work in dark mode; light mode is an opt-in toggle.
- **Theme variables** defined in `tailwind.config.js` under the `theme.extend` section.

### 3.3 Visual Style
- **Style**: Modern, Material-inspired with slight glassmorphism for modals and notifications.
- **Glassmorphism**: Use `backdrop-blur-sm`, semi-transparent backgrounds (`bg-white/10`, `bg-gray-900/50`).

### 3.4 Color Palette
- Primary: #3B82F6 (blue-500)
- Accent:  #10B981 (green-500)
- Neutral Dark: #1F2937 (gray-800)
- Neutral Light: #374151 (gray-700)
- Background: #111827 (gray-900)
- Surface (cards, panels): #1E2024
- Text Primary: #E5E7EB (gray-200)
- Text Secondary: #9CA3AF (gray-400)
- Error: #EF4444 (red-500)

### 3.5 Typography
- **Font Family**: Inter (primary), fallback sans-serif.
- **Headings**: `font-semibold`, responsive sizing (`text-xl`, `md:text-2xl`).
- **Body**: `font-normal`, `text-base`.

## 4. Component Structure

### 4.1 Organization
- **Atomic Design**: `/components/atoms`, `/components/molecules`, `/components/organisms`, `/pages`.
- Each component folder contains:
  - An HTML template (partial).
  - An optional Alpine.js initializer file (`.js`).
  - A style snippet if custom CSS is needed.

### 4.2 Reusability
- Props (`x-data` attributes) and events (`$dispatch`, `$on`) allow one component to talk to another.
- Shared utilities (`/utils/`) hold common functions (date formatting, API callers).
- ShadCN UI components customized via slots and Alpine props.

### 4.3 Benefits
- Single source of truth: update a component once and see it reflected everywhere.
- Easier on-boarding: new developers find structure intuitive.
- Isolated testing: each component has its own tests.

## 5. State Management

### 5.1 Local State
- **Alpine.js `x-data`** for per-component state (menus open/closed, form inputs).

### 5.2 Shared State
- **Alpine Stores** (`Alpine.store('user')`) hold global data like user info, theme preference, notification count.
- Components read/write to stores (`$store.theme.toggle()`).

### 5.3 Server State
- **HTMX** manages server-fetched fragments; state is kept on server and reflected in the UI.
- Combine with Alpine for progressive enhancement: HTMX swaps HTML, Alpine re-initializes behavior.

## 6. Routing and Navigation

### 6.1 Web Dashboard
- **Server-side routing** via Django URLs.
- **HTMX** can fetch partials (e.g., mail list, draft preview) at endpoints returning HTML fragments.
- **Alpine.js** for sidebar collapse, tab switching without full reload.

### 6.2 Extension UI
- **Static routes** in `manifest.json`: `popup.html`, `options.html`.
- **Anchor links** and Alpine-driven tab panels for switching between sections (e.g., categories, settings).

## 7. Performance Optimization

- **Tailwind JIT & Purge**: Removes unused CSS classes, keeping bundle small.
- **Vite Code Splitting**: Dynamically import heavy modules (e.g., transcript player) only when needed.
- **Lazy Loading**: `<img loading="lazy">` for avatars; HTMX `hx-trigger="revealed"` for on-scroll loads.
- **Defer and Async Scripts**: `<script type="module" defer>`; place at bottom of `<body>`.
- **Asset Compression**: Gzip/Brotli on server; optimized image formats (WebP).
- **Service Worker** (extension uses its own SW) for caching static assets.

## 8. Testing and Quality Assurance

### 8.1 Unit Testing
- **Vitest** with JSDOM for Alpine component logic.
- **jest-dom** matchers for DOM assertions.

### 8.2 Integration & End-to-End
- **Cypress** to simulate user flows on the dashboard: login, view emails, generate draft.
- **Playwright** for extension popup and in-inbox interactions.

### 8.3 Linting & Formatting
- **ESLint** (with plugin for Alpine.js) enforces JS conventions.
- **Stylelint** (with Tailwind config) checks CSS usage.
- **Prettier** for consistent formatting across HTML, JS, and CSS.

### 8.4 Accessibility Checks
- **axe-core** audit in CI to catch contrast or ARIA issues.
- Manual keyboard & screen reader testing on critical screens.

## 9. Conclusion and Overall Frontend Summary

We combine a server-driven approach (Django + HTMX) with lightweight client interactivity (Alpine.js) and a utility-first styling system (Tailwind CSS + ShadCN UI). This setup:

- Delivers fast load times and low latency for email categorization and draft generation.
- Ensures a consistent, accessible, and responsive interface across both the web dashboard and browser/Outlook extensions.
- Scales gracefully: component-based code, shared stores, and clear separation of concerns make it easy to onboard new features or support multiple users in future.

By following these guidelines—architecture, design principles, theming, components, state, routing, performance, and testing—our frontend remains maintainable, performant, and user-friendly as we iterate on this MVP.

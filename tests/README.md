# FYXERAI Frontend Test Suite

A comprehensive testing framework for the FYXERAI email management system, covering unit tests, integration tests, end-to-end tests, accessibility testing, and performance testing.

## 🧪 Test Overview

### Test Structure
```
tests/
├── unit/                   # Unit tests for individual components
│   ├── websocket-client.test.js
│   ├── alpine-components.test.js
│   └── chrome-extension.test.js
├── integration/            # Integration tests for system interactions
│   └── websocket-integration.test.js
├── e2e/                    # End-to-end tests using Playwright
│   ├── dashboard-flow.spec.js
│   ├── chrome-extension.spec.js
│   ├── performance.spec.js
│   └── accessibility.spec.js
├── setup.js               # Test setup and mocks
└── README.md              # This file
```

### Testing Tools & Frameworks

- **Vitest**: Fast unit and integration testing
- **Playwright**: End-to-end testing across browsers
- **@axe-core/playwright**: Automated accessibility testing
- **@testing-library/jest-dom**: DOM testing utilities
- **JSDOM**: DOM simulation for unit tests

## 🚀 Running Tests

### All Tests
```bash
npm run test:all          # Run all tests (unit + e2e)
```

### Unit Tests
```bash
npm run test              # Run unit tests in watch mode
npm run test:run          # Run unit tests once
npm run test:unit         # Run only unit tests
npm run test:coverage     # Generate coverage report
npm run test:ui           # Launch Vitest UI
```

### Integration Tests
```bash
npm run test:integration  # Run integration tests
```

### End-to-End Tests
```bash
npm run test:e2e          # Run all E2E tests headless
npm run test:e2e:headed   # Run E2E tests with browser UI
npm run test:e2e:ui       # Launch Playwright test runner UI
```

### Specialized Test Suites
```bash
npm run test:accessibility  # Test accessibility compliance
npm run test:performance    # Test performance metrics
npm run test:extension      # Test Chrome extension (headed)
```

### Setup Commands
```bash
npm run playwright:install      # Install Playwright browsers
npm run playwright:install-deps # Install system dependencies
```

## 📋 Test Categories

### 1. Unit Tests

**WebSocket Client Tests** (`websocket-client.test.js`)
- Connection establishment and management
- Message handling and parsing
- Reconnection logic and error handling
- Real-time state updates
- Notification system integration

**Alpine.js Component Tests** (`alpine-components.test.js`)
- Component initialization and state management
- Event handling and user interactions
- Theme toggling functionality
- Modal and UI component behavior
- Store integration and reactivity

**Chrome Extension Tests** (`chrome-extension.test.js`)
- Background script functionality
- Content script injection and DOM manipulation
- Message passing between scripts
- Storage operations and preferences
- API integration and authentication

### 2. Integration Tests

**WebSocket Integration** (`websocket-integration.test.js`)
- Full WebSocket connection lifecycle
- Message exchange between client and server
- Real-time synchronization features
- Error handling and recovery
- Performance under load

### 3. End-to-End Tests

**Dashboard Flow** (`dashboard-flow.spec.js`)
- Complete user workflows
- Navigation between dashboard sections
- Real-time feature functionality
- Theme switching and UI interactions
- Error handling and edge cases

**Chrome Extension E2E** (`chrome-extension.spec.js`)
- Extension installation and loading
- Integration with Gmail/Outlook interfaces
- Popup interface functionality
- Content script behavior
- API communication

**Performance Tests** (`performance.spec.js`)
- Core Web Vitals measurement
- Load time optimization
- Real-time update performance
- Memory usage monitoring
- Network performance under various conditions

**Accessibility Tests** (`accessibility.spec.js`)
- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatibility
- Color contrast validation
- Mobile accessibility
- Focus management

## 🎯 Test Coverage Goals

### Coverage Targets
- **Overall Coverage**: > 85%
- **Functions**: > 90%
- **Statements**: > 85%
- **Branches**: > 80%

### Coverage Reports
```bash
npm run test:coverage     # Generate detailed coverage report
open coverage/index.html  # View coverage report in browser
```

## 🔧 Test Configuration

### Vitest Configuration (`vitest.config.js`)
- JSDOM environment for DOM testing
- Coverage reporting with V8
- Custom test setup and mocks
- Path aliases for imports

### Playwright Configuration (`playwright.config.js`)
- Multi-browser testing (Chrome, Firefox, Safari)
- Mobile device simulation
- Screenshot and video capture
- Test parallelization
- CI/CD integration

## 🛠 Development Workflow

### Running Tests During Development
1. **Watch Mode**: `npm run test:watch` for continuous unit testing
2. **Coverage**: `npm run test:coverage` to ensure adequate coverage
3. **E2E Testing**: `npm run test:e2e:headed` for visual debugging
4. **Accessibility**: `npm run test:accessibility` before feature completion

### Pre-commit Testing
```bash
# Recommended pre-commit sequence
npm run test:run           # Fast unit tests
npm run test:accessibility # Quick accessibility check
npm run build-css-once     # Ensure CSS builds
```

### CI/CD Integration
The test suite runs automatically on:
- Push to main/develop branches
- Pull requests
- Scheduled runs (daily)

## 📊 Test Metrics & Monitoring

### Performance Budgets
- **First Contentful Paint**: < 1.5s
- **Largest Contentful Paint**: < 2.5s
- **Cumulative Layout Shift**: < 0.1
- **Time to Interactive**: < 3s

### Accessibility Standards
- **WCAG Level**: AA compliance
- **Color Contrast**: 4.5:1 minimum
- **Keyboard Navigation**: 100% operable
- **Screen Reader**: Full compatibility

### Browser Support Matrix
| Browser | Version | Status |
|---------|---------|--------|
| Chrome | Latest 2 | ✅ Full |
| Firefox | Latest 2 | ✅ Full |
| Safari | Latest 2 | ✅ Full |
| Edge | Latest 2 | ✅ Full |
| Mobile Chrome | Latest | ✅ Full |
| Mobile Safari | Latest | ✅ Full |

## 🐛 Debugging Tests

### Common Issues
1. **WebSocket Connection Failures**
   - Ensure Redis is running for integration tests
   - Check Django server is started for E2E tests

2. **Extension Tests**
   - Run with `--headed` flag to see browser interactions
   - Check extension manifest and permissions

3. **Playwright Timeouts**
   - Increase timeout for slow operations
   - Use `page.waitForLoadState('networkidle')` for async content

### Debug Commands
```bash
# Debug specific test file
npx vitest run tests/unit/websocket-client.test.js

# Debug E2E test with browser open
npx playwright test tests/e2e/dashboard-flow.spec.js --headed --debug

# Run single test with detailed output
npx playwright test --grep "should load dashboard" --headed
```

## 📈 Test Quality Metrics

### Automated Quality Checks
- **Code Coverage**: Minimum thresholds enforced
- **Performance Budgets**: Core Web Vitals monitoring
- **Accessibility Score**: Automated axe-core scanning
- **Cross-browser Compatibility**: Multi-browser test execution

### Quality Gates
Tests must pass these gates before merging:
1. ✅ All unit tests pass
2. ✅ Integration tests pass
3. ✅ E2E tests pass on all browsers
4. ✅ Accessibility tests have no violations
5. ✅ Performance tests meet budgets
6. ✅ Extension tests pass
7. ✅ Code coverage meets minimum thresholds

## 🔄 Continuous Improvement

### Regular Maintenance
- **Weekly**: Review test results and flaky tests
- **Monthly**: Update dependencies and browser versions
- **Quarterly**: Review and update test coverage goals
- **Annually**: Comprehensive test suite architecture review

### Adding New Tests
1. **Unit Tests**: Add for new components/functions
2. **Integration Tests**: Add for new feature integrations
3. **E2E Tests**: Add for new user workflows
4. **Accessibility Tests**: Add for new UI components
5. **Performance Tests**: Add for new performance-critical features

### Test Data Management
- Use factories for consistent test data
- Mock external dependencies
- Clean up test data after each test
- Avoid test interdependencies

---

## 📞 Support & Contributing

For questions about the test suite:
1. Check this documentation
2. Review existing test examples
3. Check CI/CD logs for failures
4. Ask in team discussions

When adding new tests:
1. Follow existing patterns and naming conventions
2. Include both positive and negative test cases
3. Add appropriate documentation
4. Ensure tests are deterministic and fast
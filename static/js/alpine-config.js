/**
 * Alpine.js Configuration and Global Stores
 * Initialize Alpine.js with global stores and component patterns
 */

// Initialize Alpine stores before Alpine starts
document.addEventListener('alpine:init', () => {
    // Theme Store - handles dark/light mode switching
    Alpine.store('theme', {
        current: localStorage.getItem('theme') || 'dark',
        
        init() {
            this.apply();
        },
        
        toggle() {
            this.current = this.current === 'dark' ? 'light' : 'dark';
            localStorage.setItem('theme', this.current);
            this.apply();
        },
        
        apply() {
            if (this.current === 'dark') {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        }
    });
    
    // User Preferences Store - handles user settings and preferences
    Alpine.store('preferences', {
        email: {
            autoRefresh: JSON.parse(localStorage.getItem('pref_auto_refresh') || 'true'),
            refreshInterval: parseInt(localStorage.getItem('pref_refresh_interval') || '300'),
            notifications: JSON.parse(localStorage.getItem('pref_notifications') || 'true'),
        },
        
        ui: {
            sidebarCollapsed: JSON.parse(localStorage.getItem('pref_sidebar_collapsed') || 'false'),
            density: localStorage.getItem('pref_ui_density') || 'comfortable',
            animation: JSON.parse(localStorage.getItem('pref_animation') || 'true'),
        },
        
        updateEmail(key, value) {
            this.email[key] = value;
            localStorage.setItem(`pref_${key}`, JSON.stringify(value));
        },
        
        updateUI(key, value) {
            this.ui[key] = value;
            localStorage.setItem(`pref_${key}`, JSON.stringify(value));
        }
    });
    
    // Application State Store - handles global app state
    Alpine.store('app', {
        loading: false,
        connected: true,
        accounts: [],
        activeAccount: null,
        
        setLoading(state) {
            this.loading = state;
        },
        
        setConnected(state) {
            this.connected = state;
        },
        
        setAccounts(accounts) {
            this.accounts = accounts;
            if (accounts.length > 0 && !this.activeAccount) {
                this.activeAccount = accounts[0];
            }
        },
        
        setActiveAccount(account) {
            this.activeAccount = account;
            localStorage.setItem('active_account_id', account?.id || '');
        }
    });
});

// Alpine.js Component Patterns and Utilities
window.AlpineComponents = {
    // Theme Toggle Component
    themeToggle() {
        return {
            get isDark() {
                return this.$store.theme.current === 'dark';
            },
            
            toggle() {
                this.$store.theme.toggle();
            }
        };
    },
    
    // Modal Component
    modal() {
        return {
            open: false,
            
            show() {
                this.open = true;
                document.body.style.overflow = 'hidden';
            },
            
            hide() {
                this.open = false;
                document.body.style.overflow = '';
            },
            
            toggle() {
                this.open ? this.hide() : this.show();
            }
        };
    },
    
    // Dropdown Component
    dropdown() {
        return {
            open: false,
            
            show() {
                this.open = true;
            },
            
            hide() {
                this.open = false;
            },
            
            toggle() {
                this.open = !this.open;
            }
        };
    },
    
    // Toast Notification Component
    toast() {
        return {
            show: false,
            message: '',
            type: 'info', // info, success, warning, error
            duration: 3000,
            
            display(message, type = 'info', duration = 3000) {
                this.message = message;
                this.type = type;
                this.duration = duration;
                this.show = true;
                
                setTimeout(() => {
                    this.hide();
                }, duration);
            },
            
            hide() {
                this.show = false;
            }
        };
    },
    
    // Loading State Component
    loadingState() {
        return {
            get isLoading() {
                return this.$store.app.loading;
            }
        };
    },
    
    // Form Component with validation
    form(initialData = {}) {
        return {
            data: { ...initialData },
            errors: {},
            submitting: false,
            
            setField(field, value) {
                this.data[field] = value;
                // Clear error when user starts typing
                if (this.errors[field]) {
                    delete this.errors[field];
                }
            },
            
            setErrors(errors) {
                this.errors = errors;
            },
            
            clearErrors() {
                this.errors = {};
            },
            
            hasError(field) {
                return !!this.errors[field];
            },
            
            getError(field) {
                return this.errors[field];
            },
            
            async submit(url, method = 'POST') {
                this.submitting = true;
                this.clearErrors();
                
                try {
                    const response = await fetch(url, {
                        method,
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                        },
                        body: JSON.stringify(this.data)
                    });
                    
                    const result = await response.json();
                    
                    if (!response.ok) {
                        if (result.errors) {
                            this.setErrors(result.errors);
                        }
                        throw new Error(result.message || 'Form submission failed');
                    }
                    
                    return result;
                } finally {
                    this.submitting = false;
                }
            }
        };
    }
};

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
    // Apply theme immediately to prevent flash
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark');
    }
});

// Alpine.js Event Utilities
window.AlpineUtils = {
    // Debounce utility for search inputs
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Throttle utility for scroll events
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // Format utilities
    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    },
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};
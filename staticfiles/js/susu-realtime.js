/**
 * Susu System Real-time Updates
 * Handles loan status monitoring and notifications
 */

// Global configuration
const SUSU_CONFIG = {
    LOAN_UPDATE_INTERVAL: 3000, // 3 seconds for R7 requirement
    NOTIFICATION_CHECK_INTERVAL: 10000, // 10 seconds
    TOAST_DURATION: 5000
};

/**
 * Utility functions
 */
const SusuUtils = {
    // Get CSRF token for Django
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        // Fallback: try to get from meta tag
        const csrfMeta = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfMeta ? csrfMeta.value : null;
    },

    // Format date for display
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString();
    },

    // Show loading spinner
    showLoading(element) {
        if (element) {
            element.innerHTML = '<div class="loading-spinner mx-auto"></div>';
        }
    },

    // API request wrapper
    async apiRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'Content-Type': 'application/json',
            }
        };

        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.json();
    }
};

/**
 * Loan Status Monitor Class
 * Handles real-time loan status updates (R7 requirement)
 */
class LoanStatusMonitor {
    constructor(options = {}) {
        this.loanElements = document.querySelectorAll('[data-loan-id]');
        this.intervalId = null;
        this.updateInterval = options.updateInterval || SUSU_CONFIG.LOAN_UPDATE_INTERVAL;
        this.isMonitoring = false;
        
        this.init();
    }

    init() {
        if (this.loanElements.length > 0) {
            console.log(`🔄 Initializing loan monitor for ${this.loanElements.length} loan(s)`);
            this.startMonitoring();
            this.setupVisibilityHandler();
        } else {
            console.log('📋 No loans found on this page');
        }
    }

    setupVisibilityHandler() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopMonitoring();
                console.log('⏸️ Paused loan monitoring (page hidden)');
            } else if (this.loanElements.length > 0) {
                this.startMonitoring();
                console.log('▶️ Resumed loan monitoring (page visible)');
            }
        });
    }

    startMonitoring() {
        if (this.intervalId || this.isMonitoring) {
            return; // Already monitoring
        }
        
        this.isMonitoring = true;
        this.intervalId = setInterval(() => {
            this.checkAllLoanStatuses();
        }, this.updateInterval);
        
        // Initial check
        this.checkAllLoanStatuses();
    }

    stopMonitoring() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.isMonitoring = false;
    }

    async checkAllLoanStatuses() {
        if (!this.isMonitoring) return;

        const promises = Array.from(this.loanElements).map(element => {
            const loanId = element.getAttribute('data-loan-id');
            return this.checkLoanStatus(loanId, element);
        });

        try {
            await Promise.all(promises);
        } catch (error) {
            console.error('❌ Error checking loan statuses:', error);
        }
    }

    async checkLoanStatus(loanId, element) {
        try {
            const data = await SusuUtils.apiRequest(`/api/loan/${loanId}/status/`);
            this.updateLoanElement(element, data);
        } catch (error) {
            console.error(`❌ Error checking loan ${loanId}:`, error);
            // Don't show error to user for individual loan failures
        }
    }

    updateLoanElement(element, loanData) {
        const currentStatus = element.getAttribute('data-current-status');
        const hasStatusChanged = currentStatus && currentStatus !== loanData.status;

        // Update status badge
        this.updateStatusBadge(element, loanData);
        
        // Update status text
        this.updateStatusText(element, loanData);
        
        // Update timestamp
        this.updateTimestamp(element, loanData);
        
        // Update approval info
        this.updateApprovalInfo(element, loanData);

        // Handle status changes
        if (hasStatusChanged) {
            this.handleStatusChange(element, loanData, currentStatus);
        }
        
        // Update current status
        element.setAttribute('data-current-status', loanData.status);
    }

    updateStatusBadge(element, loanData) {
        const statusBadge = element.querySelector('.loan-status-badge');
        if (!statusBadge) return;

        const badgeClass = this.getStatusBadgeClass(loanData.status);
        statusBadge.className = `loan-status-badge badge ${badgeClass}`;
        statusBadge.textContent = loanData.status_display;
        
        // Add update animation
        statusBadge.classList.add('status-updated');
        setTimeout(() => statusBadge.classList.remove('status-updated'), 1000);
    }

    updateStatusText(element, loanData) {
        const statusText = element.querySelector('.loan-status-text');
        if (statusText) {
            statusText.textContent = loanData.status_display;
        }
    }

    updateTimestamp(element, loanData) {
        const lastUpdated = element.querySelector('.last-updated');
        if (!lastUpdated) return;

        const timestampSpan = lastUpdated.querySelector('span') || lastUpdated;
        const formattedTime = SusuUtils.formatDate(loanData.last_updated);
        
        if (timestampSpan.tagName === 'SPAN') {
            timestampSpan.textContent = formattedTime;
        } else {
            timestampSpan.innerHTML = `<i class="fas fa-sync-alt"></i> Last updated: ${formattedTime}`;
        }
    }

    updateApprovalInfo(element, loanData) {
        const approvalInfo = element.querySelector('.approval-info');
        if (!approvalInfo) return;

        let infoHtml = '';
        
        if (loanData.status === 'approved' && loanData.date_approved) {
            infoHtml = `
                <small class="text-success">
                    <i class="fas fa-check-circle"></i>
                    Approved on ${SusuUtils.formatDate(loanData.date_approved)} 
                    by ${loanData.approved_by || 'Admin'}
                </small>
            `;
        } else if (loanData.status === 'rejected' && loanData.rejection_reason) {
            infoHtml = `
                <small class="text-danger">
                    <i class="fas fa-times-circle"></i>
                    Rejected: ${loanData.rejection_reason}
                </small>
            `;
        }
        
        approvalInfo.innerHTML = infoHtml;
    }

    handleStatusChange(element, loanData, previousStatus) {
        console.log(`📊 Loan status changed: ${previousStatus} → ${loanData.status}`);
        
        // Show toast notification
        this.showStatusChangeToast(loanData, previousStatus);
        
        // Update card styling if needed
        this.updateCardStyling(element, loanData.status);
        
        // Trigger custom event for other components
        const event = new CustomEvent('loanStatusChanged', {
            detail: { loanData, previousStatus, element }
        });
        document.dispatchEvent(event);
    }

    updateCardStyling(element, status) {
        // Remove existing status classes
        element.classList.remove('status-pending', 'status-approved', 'status-rejected', 'status-disbursed');
        
        // Add new status class
        element.classList.add(`status-${status}`);
    }

    getStatusBadgeClass(status) {
        const statusClasses = {
            'pending': 'badge-warning',
            'approved': 'badge-success',
            'rejected': 'badge-danger',
            'disbursed': 'badge-info',
            'repaid': 'badge-secondary',
            'defaulted': 'badge-dark'
        };
        
        return statusClasses[status] || 'badge-secondary';
    }

    showStatusChangeToast(loanData, previousStatus) {
        const title = '📊 Loan Status Update';
        const message = `Status changed from "${previousStatus}" to "${loanData.status_display}"`;
        
        SusuToast.show(title, message, 'info');
    }

    // Public method to manually refresh all loans
    refresh() {
        console.log('🔄 Manual loan status refresh triggered');
        this.checkAllLoanStatuses();
    }
}

/**
 * Notification Monitor Class
 * Handles notification badge and dropdown updates
 */
class NotificationMonitor {
    constructor() {
        this.badgeElement = document.getElementById('notification-count');
        this.previewElement = document.getElementById('notification-preview');
        this.dropdownTrigger = document.getElementById('notificationDropdown');
        this.intervalId = null;
        
        this.init();
    }

    init() {
        if (!this.badgeElement) {
            console.log('📝 Notification badge not found - notifications disabled');
            return;
        }

        console.log('📝 Initializing notification monitor');
        this.checkUnreadCount();
        this.startMonitoring();
        this.setupDropdownHandler();
    }

    startMonitoring() {
        this.intervalId = setInterval(() => {
            this.checkUnreadCount();
        }, SUSU_CONFIG.NOTIFICATION_CHECK_INTERVAL);
    }

    setupDropdownHandler() {
        if (this.dropdownTrigger) {
            this.dropdownTrigger.addEventListener('click', () => {
                this.loadNotificationPreview();
            });
        }
    }

    async checkUnreadCount() {
        try {
            const data = await SusuUtils.apiRequest('/api/notifications/unread-count/');
            this.updateBadge(data.count);
        } catch (error) {
            console.error('❌ Error checking notification count:', error);
        }
    }

    updateBadge(count) {
        if (!this.badgeElement) return;

        if (count > 0) {
            this.badgeElement.textContent = count > 99 ? '99+' : count;
            this.badgeElement.style.display = 'inline';
        } else {
            this.badgeElement.style.display = 'none';
        }
    }

    async loadNotificationPreview() {
        if (!this.previewElement) return;
        
        SusuUtils.showLoading(this.previewElement);

        try {
            // Simulate loading (you can implement actual preview endpoint)
            await new Promise(resolve => setTimeout(resolve, 500));
            
            this.previewElement.innerHTML = `
                <div class="dropdown-item text-center text-muted">
                    <i class="fas fa-bell"></i>
                    <small>Click "View All" to see notifications</small>
                </div>
            `;
        } catch (error) {
            console.error('❌ Error loading notification preview:', error);
            this.previewElement.innerHTML = `
                <div class="dropdown-item text-center text-danger">
                    <small>Error loading notifications</small>
                </div>
            `;
        }
    }

    // Public method to manually refresh notifications
    refresh() {
        console.log('📝 Manual notification refresh triggered');
        this.checkUnreadCount();
    }
}

/**
 * Toast Notification System
 */
class SusuToast {
    static show(title, message, type = 'info', duration = SUSU_CONFIG.TOAST_DURATION) {
        const toastContainer = this.getOrCreateContainer();
        const toastId = 'toast-' + Date.now();
        
        const toastHtml = `
            <div class="toast" id="${toastId}" role="alert" data-autohide="true" data-delay="${duration}">
                <div class="toast-header">
                    <i class="fas fa-${this.getIcon(type)} text-${type} mr-2"></i>
                    <strong class="mr-auto">${title}</strong>
                    <small class="text-muted">${new Date().toLocaleTimeString()}</small>
                    <button type="button" class="ml-2 mb-1 close" data-dismiss="toast">
                        <span>&times;</span>
                    </button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Show the toast
        const toastElement = document.getElementById(toastId);
        if (typeof $ !== 'undefined' && $.fn.toast) {
            $(toastElement).toast('show');
            $(toastElement).on('hidden.bs.toast', function() {
                this.remove();
            });
        } else {
            // Fallback for non-Bootstrap environments
            toastElement.style.display = 'block';
            setTimeout(() => toastElement.remove(), duration);
        }
    }

    static getOrCreateContainer() {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed';
            container.style.cssText = 'top: 20px; right: 20px; z-index: 1050;';
            document.body.appendChild(container);
        }
        return container;
    }

    static getIcon(type) {
        const icons = {
            'success': 'check-circle',
            'info': 'info-circle',
            'warning': 'exclamation-triangle',
            'danger': 'times-circle',
            'error': 'times-circle'
        };
        return icons[type] || 'bell';
    }
}

/**
 * Real-time Dashboard Updates
 */
class DashboardMonitor {
    constructor() {
        this.statsElements = document.querySelectorAll('[data-stat-type]');
        this.intervalId = null;
        this.init();
    }

    init() {
        if (this.statsElements.length > 0) {
            console.log('📈 Initializing dashboard monitor');
            this.startMonitoring();
        }
    }

    startMonitoring() {
        // Update dashboard stats every 30 seconds
        this.intervalId = setInterval(() => {
            this.updateDashboardStats();
        }, 30000);
    }

    async updateDashboardStats() {
        // This would need a backend endpoint to provide updated stats
        try {
            const data = await SusuUtils.apiRequest('/api/dashboard/stats/');
            this.updateStatsElements(data);
        } catch (error) {
            console.error('❌ Error updating dashboard stats:', error);
        }
    }

    updateStatsElements(data) {
        this.statsElements.forEach(element => {
            const statType = element.getAttribute('data-stat-type');
            if (data[statType] !== undefined) {
                element.textContent = data[statType];
                
                // Add update animation
                element.classList.add('stat-updated');
                setTimeout(() => element.classList.remove('stat-updated'), 500);
            }
        });
    }
}

/**
 * Form Enhancement Utilities
 */
class SusuForms {
    static init() {
        // Auto-submit forms with data-auto-submit attribute
        document.querySelectorAll('form[data-auto-submit]').forEach(form => {
            const delay = parseInt(form.getAttribute('data-auto-submit')) || 1000;
            this.setupAutoSubmit(form, delay);
        });

        // Real-time form validation
        document.querySelectorAll('.needs-validation').forEach(form => {
            this.setupRealTimeValidation(form);
        });

        // Enhanced file upload with preview
        document.querySelectorAll('input[type="file"][data-preview]').forEach(input => {
            this.setupFilePreview(input);
        });
    }

    static setupAutoSubmit(form, delay) {
        let timeoutId;
        
        form.addEventListener('input', () => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                form.submit();
            }, delay);
        });
    }

    static setupRealTimeValidation(form) {
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
        });
    }

    static validateField(field) {
        const isValid = field.checkValidity();
        
        field.classList.remove('is-valid', 'is-invalid');
        field.classList.add(isValid ? 'is-valid' : 'is-invalid');
        
        // Show/hide feedback
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.style.display = isValid ? 'none' : 'block';
        }
    }

    static setupFilePreview(input) {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const previewContainer = document.querySelector(input.getAttribute('data-preview'));
            if (!previewContainer) return;

            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewContainer.innerHTML = `
                        <img src="${e.target.result}" class="img-thumbnail" style="max-width: 200px;">
                    `;
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

/**
 * Keyboard Shortcuts
 */
class SusuShortcuts {
    static init() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + R: Refresh loan statuses
            if ((e.ctrlKey || e.metaKey) && e.key === 'r' && e.shiftKey) {
                e.preventDefault();
                if (window.susuLoanMonitor) {
                    window.susuLoanMonitor.refresh();
                    SusuToast.show('🔄 Refresh', 'Loan statuses refreshed', 'info');
                }
            }

            // Ctrl/Cmd + N: Quick add customer (if on customers page)
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                const addCustomerBtn = document.querySelector('[href*="add_customer"]');
                if (addCustomerBtn) {
                    e.preventDefault();
                    addCustomerBtn.click();
                }
            }

            // Escape: Close modals
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal && typeof $ !== 'undefined') {
                    $(openModal).modal('hide');
                }
            }
        });
    }
}

/**
 * Connection Status Monitor
 */
class ConnectionMonitor {
    constructor() {
        this.isOnline = navigator.onLine;
        this.indicator = null;
        this.init();
    }

    init() {
        this.createIndicator();
        
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateIndicator();
            SusuToast.show('🌐 Connection', 'Back online', 'success');
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateIndicator();
            SusuToast.show('🌐 Connection', 'Connection lost', 'warning');
        });
    }

    createIndicator() {
        this.indicator = document.querySelector('.real-time-indicator');
        if (this.indicator) {
            this.updateIndicator();
        }
    }

    updateIndicator() {
        if (!this.indicator) return;

        if (this.isOnline) {
            this.indicator.style.backgroundColor = '#28a745';
            this.indicator.title = 'Online - Real-time updates active';
        } else {
            this.indicator.style.backgroundColor = '#dc3545';
            this.indicator.title = 'Offline - Real-time updates paused';
        }
    }
}

/**
 * Main initialization
 */
class SusuSystem {
    static init() {
        console.log('🏦 Susu System JavaScript initialized');
        
        // Initialize all components
        window.susuLoanMonitor = new LoanStatusMonitor();
        window.susuNotificationMonitor = new NotificationMonitor();
        window.susuDashboardMonitor = new DashboardMonitor();
        window.susuConnectionMonitor = new ConnectionMonitor();
        
        // Initialize utilities
        SusuForms.init();
        SusuShortcuts.init();
        
        // Global error handler
        window.addEventListener('error', (e) => {
            console.error('🚨 JavaScript Error:', e.error);
        });

        // Global AJAX error handler
        if (typeof $ !== 'undefined') {
            $(document).ajaxError((event, xhr, settings, error) => {
                console.error('🚨 AJAX Error:', error);
                if (xhr.status >= 400) {
                    SusuToast.show('⚠️ Error', 'Network request failed', 'danger');
                }
            });
        }

        console.log('✅ Susu System fully loaded');
    }

    static refresh() {
        // Refresh all monitors
        if (window.susuLoanMonitor) window.susuLoanMonitor.refresh();
        if (window.susuNotificationMonitor) window.susuNotificationMonitor.refresh();
        
        SusuToast.show('🔄 System', 'All data refreshed', 'info');
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', SusuSystem.init);
} else {
    SusuSystem.init();
}

// Export for global access
window.Susu = {
    System: SusuSystem,
    LoanMonitor: LoanStatusMonitor,
    NotificationMonitor: NotificationMonitor,
    Toast: SusuToast,
    Utils: SusuUtils
};
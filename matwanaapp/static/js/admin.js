// Admin Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Password strength checker
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        if (input.id === 'password' || input.name === 'password') {
            input.addEventListener('input', function() {
                checkPasswordStrength(this.value);
            });
        }
    });
    
    // Confirm password match
    const confirmPasswordInputs = document.querySelectorAll('input[name="confirm_password"]');
    confirmPasswordInputs.forEach(input => {
        input.addEventListener('input', function() {
            const password = document.querySelector('input[name="password"]')?.value;
            const confirmPassword = this.value;
            
            if (password && confirmPassword) {
                const matchIndicator = document.getElementById('passwordMatch') || 
                                      this.nextElementSibling?.querySelector('.password-match');
                
                if (matchIndicator) {
                    if (password === confirmPassword) {
                        matchIndicator.textContent = 'Passwords match ✓';
                        matchIndicator.className = 'password-match valid';
                    } else {
                        matchIndicator.textContent = 'Passwords do not match ✗';
                        matchIndicator.className = 'password-match invalid';
                    }
                }
            }
        });
    });
    
    // Table row selection
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('input[name="selected_items"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }
    
    // Bulk actions
    const bulkActionSelect = document.getElementById('bulkAction');
    if (bulkActionSelect) {
        bulkActionSelect.addEventListener('change', function() {
            if (this.value) {
                const selectedItems = Array.from(document.querySelectorAll('input[name="selected_items"]:checked'))
                    .map(checkbox => checkbox.value);
                
                if (selectedItems.length === 0) {
                    alert('Please select items to perform this action.');
                    this.value = '';
                    return;
                }
                
                if (confirm(`Are you sure you want to ${this.options[this.selectedIndex].text.toLowerCase()} ${selectedItems.length} item(s)?`)) {
                    // Submit bulk action form
                    document.getElementById('bulkActionForm').submit();
                } else {
                    this.value = '';
                }
            }
        });
    }
    
    // Date pickers
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            const today = new Date().toISOString().split('T')[0];
            input.value = today;
        }
    });
    
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.form.submit();
            }, 500);
        });
    }
    
    // Filter form auto-submit
    const filterSelects = document.querySelectorAll('.filter-select');
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            this.form.submit();
        });
    });
    
    // Toggle advanced filters
    const toggleFiltersBtn = document.getElementById('toggleFilters');
    if (toggleFiltersBtn) {
        toggleFiltersBtn.addEventListener('click', function() {
            const filtersSection = document.getElementById('advancedFilters');
            filtersSection.classList.toggle('d-none');
            this.innerHTML = filtersSection.classList.contains('d-none') ? 
                '<i class="fas fa-filter me-2"></i> Show Filters' : 
                '<i class="fas fa-times me-2"></i> Hide Filters';
        });
    }
    
    // Export data
    const exportButtons = document.querySelectorAll('.export-btn');
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const format = this.dataset.format || 'csv';
            const url = new URL(window.location.href);
            url.searchParams.set('export', format);
            window.location.href = url.toString();
        });
    });
    
    // Print functionality
    const printBtn = document.getElementById('printBtn');
    if (printBtn) {
        printBtn.addEventListener('click', function() {
            window.print();
        });
    }
    
    // Refresh data
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            this.classList.add('loading');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        });
    }
    
    // Mobile menu toggle (for responsive design)
    const mobileMenuToggle = document.createElement('button');
    mobileMenuToggle.className = 'mobile-menu-toggle d-lg-none';
    mobileMenuToggle.innerHTML = '<i class="fas fa-bars"></i>';
    mobileMenuToggle.addEventListener('click', function() {
        document.querySelector('.sidebar').classList.toggle('active');
    });
    document.body.appendChild(mobileMenuToggle);
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        const sidebar = document.querySelector('.sidebar');
        const mobileToggle = document.querySelector('.mobile-menu-toggle');
        
        if (sidebar.classList.contains('active') && 
            !sidebar.contains(event.target) && 
            !mobileToggle.contains(event.target)) {
            sidebar.classList.remove('active');
        }
    });
});

// Password strength checker function
function checkPasswordStrength(password) {
    if (!password) return;
    
    const strengthBar = document.getElementById('strengthBar');
    if (!strengthBar) return;
    
    let strength = 0;
    const rules = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };
    
    // Update rules display
    Object.keys(rules).forEach(rule => {
        const ruleElement = document.getElementById(`rule${rule.charAt(0).toUpperCase() + rule.slice(1)}`);
        if (ruleElement) {
            ruleElement.className = rules[rule] ? 'valid' : '';
        }
        if (rules[rule]) strength++;
    });
    
    // Update strength bar
    strengthBar.className = 'strength-bar';
    const percentage = (strength / 5) * 100;
    strengthBar.style.width = percentage + '%';
    
    if (strength <= 2) {
        strengthBar.classList.add('strength-weak');
    } else if (strength <= 4) {
        strengthBar.classList.add('strength-medium');
    } else {
        strengthBar.classList.add('strength-strong');
    }
}

// Show notification function
function showNotification(type, message, duration = 5000) {
    const container = document.querySelector('.notifications-container') || createNotificationsContainer();
    
    const notification = document.createElement('div');
    notification.className = `notification alert alert-${type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(notification);
        bsAlert.close();
    }, duration);
}

function createNotificationsContainer() {
    const container = document.createElement('div');
    container.className = 'notifications-container';
    document.body.appendChild(container);
    return container;
}

// Confirmation dialog
function confirmAction(message, callback) {
    if (confirm(message)) {
        if (typeof callback === 'function') {
            callback();
        }
        return true;
    }
    return false;
}

// Load data via AJAX
async function loadData(url, options = {}) {
    try {
        const response = await fetch(url, {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                ...options.headers
            },
            body: options.body ? JSON.stringify(options.body) : null
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error loading data:', error);
        showNotification('danger', 'Error loading data. Please try again.');
        throw error;
    }
}

// Get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Format date
function formatDate(dateString, format = 'medium') {
    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: format === 'short' ? 'short' : 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleDateString('en-US', options);
}

// Format currency
function formatCurrency(amount, currency = 'KES') {
    return new Intl.NumberFormat('en-KE', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2
    }).format(amount);
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
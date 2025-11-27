// File: static/js/forum.js

/**
 * Forum JavaScript Enhancements
 * Integrates with backend sentiment analysis and content detection algorithms
 */

class ForumEnhancements {
    constructor() {
        this.init();
    }

    init() {
        this.setupRealTimeContentAnalysis();
        this.setupVoteButtons();
        this.setupFollowButtons();
        this.setupAutoSave();
        this.setupNotificationPolling();
        this.setupSearchEnhancements();
        this.setupKeyboardShortcuts();
    }

    /**
     * Real-time content analysis as user types
     * Provides feedback on potentially inappropriate content
     */
    setupRealTimeContentAnalysis() {
        const contentFields = document.querySelectorAll('textarea[name="content"], input[name="title"]');
        
        if (contentFields.length === 0) return;

        // Inappropriate keywords (simplified version)
        const inappropriatePatterns = [
            /\b(spam|scam|fake)\b/i,
            /\b(hate|racist)\b/i,
            /\b(cheat|plagiar)\b/i
        ];

        const suspiciousPatterns = [
            /\b(password|login)\b/i,
            /\b(free.?money|earn.?fast)\b/i
        ];

        contentFields.forEach(field => {
            let analysisTimeout;
            const feedbackDiv = this.createFeedbackDiv(field);

            field.addEventListener('input', () => {
                clearTimeout(analysisTimeout);
                analysisTimeout = setTimeout(() => {
                    this.analyzeContent(field.value, feedbackDiv, inappropriatePatterns, suspiciousPatterns);
                }, 500);
            });
        });
    }

    createFeedbackDiv(field) {
        const existing = field.parentElement.querySelector('.content-feedback');
        if (existing) return existing;

        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'content-feedback mt-2';
        feedbackDiv.style.display = 'none';
        field.parentElement.appendChild(feedbackDiv);
        return feedbackDiv;
    }

    analyzeContent(text, feedbackDiv, inappropriatePatterns, suspiciousPatterns) {
        if (!text || text.length < 10) {
            feedbackDiv.style.display = 'none';
            return;
        }

        const issues = [];
        
        // Check for inappropriate content
        inappropriatePatterns.forEach(pattern => {
            if (pattern.test(text)) {
                issues.push({
                    type: 'error',
                    message: 'Your content may contain inappropriate language'
                });
            }
        });

        // Check for suspicious content
        suspiciousPatterns.forEach(pattern => {
            if (pattern.test(text)) {
                issues.push({
                    type: 'warning',
                    message: 'Your content may be flagged for review'
                });
            }
        });

        // Check for excessive caps
        const capsRatio = (text.match(/[A-Z]/g) || []).length / text.length;
        if (capsRatio > 0.5 && text.length > 20) {
            issues.push({
                type: 'warning',
                message: 'Using too many CAPITAL letters may appear as shouting'
            });
        }

        // Check for excessive punctuation
        if ((text.match(/[!?]{3,}/g) || []).length > 0) {
            issues.push({
                type: 'info',
                message: 'Excessive punctuation may reduce readability'
            });
        }

        // Display feedback
        if (issues.length > 0) {
            feedbackDiv.innerHTML = issues.map(issue => `
                <div class="alert alert-${issue.type === 'error' ? 'danger' : issue.type === 'warning' ? 'warning' : 'info'} alert-dismissible fade show py-2" role="alert">
                    <i class='bx ${issue.type === 'error' ? 'bx-error' : issue.type === 'warning' ? 'bx-error-circle' : 'bx-info-circle'}'></i>
                    ${issue.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `).join('');
            feedbackDiv.style.display = 'block';
        } else {
            feedbackDiv.style.display = 'none';
        }
    }

    /**
     * Setup vote buttons with AJAX
     */
    setupVoteButtons() {
        // Post upvote buttons
        document.querySelectorAll('.upvote-btn').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                const postId = this.dataset.postId;
                const isUpvoted = this.dataset.upvoted === 'true';

                try {
                    const response = await fetch(`/forum/post/${postId}/upvote/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken'),
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    if (response.ok) {
                        const data = await response.json();
                        this.dataset.upvoted = data.upvoted;
                        this.querySelector('.upvote-count').textContent = data.upvote_count;

                        if (data.upvoted) {
                            this.classList.remove('btn-outline-primary');
                            this.classList.add('btn-primary');
                            this.classList.add('animate-vote');
                        } else {
                            this.classList.remove('btn-primary');
                            this.classList.add('btn-outline-primary');
                        }

                        setTimeout(() => this.classList.remove('animate-vote'), 300);
                    }
                } catch (error) {
                    console.error('Error upvoting:', error);
                    showToast('Error', 'Failed to update vote', 'error');
                }
            });
        });

        // Reply upvote buttons
        document.querySelectorAll('.reply-upvote-btn').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                const replyId = this.dataset.replyId;

                try {
                    const response = await fetch(`/forum/reply/${replyId}/upvote/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken'),
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    if (response.ok) {
                        const data = await response.json();
                        this.querySelector('.reply-upvote-count').textContent = data.upvote_count;

                        if (data.upvoted) {
                            this.classList.remove('btn-outline-primary');
                            this.classList.add('btn-primary');
                            this.classList.add('animate-vote');
                        } else {
                            this.classList.remove('btn-primary');
                            this.classList.add('btn-outline-primary');
                        }

                        setTimeout(() => this.classList.remove('animate-vote'), 300);
                    }
                } catch (error) {
                    console.error('Error upvoting reply:', error);
                }
            });
        });
    }

    /**
     * Setup follow buttons
     */
    setupFollowButtons() {
        document.querySelectorAll('.follow-btn').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                const postId = this.dataset.postId;

                try {
                    const response = await fetch(`/forum/post/${postId}/follow/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken'),
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    if (response.ok) {
                        const data = await response.json();
                        this.dataset.following = data.following;
                        const icon = this.querySelector('i');
                        const text = this.lastChild;

                        if (data.following) {
                            icon.className = 'bx bx-check';
                            this.classList.remove('btn-outline-secondary');
                            this.classList.add('btn-success');
                            text.textContent = ' Following';
                            showToast('Success', 'You are now following this post', 'success');
                        } else {
                            icon.className = 'bx bx-bell';
                            this.classList.remove('btn-success');
                            this.classList.add('btn-outline-secondary');
                            text.textContent = ' Follow';
                            showToast('Success', 'You unfollowed this post', 'info');
                        }
                    }
                } catch (error) {
                    console.error('Error following post:', error);
                    showToast('Error', 'Failed to update follow status', 'error');
                }
            });
        });
    }

    /**
     * Auto-save draft posts
     */
    setupAutoSave() {
        const form = document.getElementById('post-form');
        if (!form) return;

        const titleInput = form.querySelector('input[name="title"]');
        const contentInput = form.querySelector('textarea[name="content"]');
        
        if (!titleInput || !contentInput) return;

        let autoSaveTimeout;
        const AUTOSAVE_KEY = 'forum_post_draft';

        // Load draft on page load
        const draft = this.loadDraft(AUTOSAVE_KEY);
        if (draft) {
            if (confirm('You have an unsaved draft. Would you like to restore it?')) {
                titleInput.value = draft.title;
                contentInput.value = draft.content;
            } else {
                this.clearDraft(AUTOSAVE_KEY);
            }
        }

        // Auto-save on input
        [titleInput, contentInput].forEach(input => {
            input.addEventListener('input', () => {
                clearTimeout(autoSaveTimeout);
                autoSaveTimeout = setTimeout(() => {
                    this.saveDraft(AUTOSAVE_KEY, {
                        title: titleInput.value,
                        content: contentInput.value,
                        timestamp: new Date().toISOString()
                    });
                    this.showAutoSaveIndicator();
                }, 2000);
            });
        });

        // Clear draft on successful submit
        form.addEventListener('submit', () => {
            this.clearDraft(AUTOSAVE_KEY);
        });
    }

    saveDraft(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
        } catch (e) {
            console.error('Error saving draft:', e);
        }
    }

    loadDraft(key) {
        try {
            const draft = localStorage.getItem(key);
            return draft ? JSON.parse(draft) : null;
        } catch (e) {
            console.error('Error loading draft:', e);
            return null;
        }
    }

    clearDraft(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error('Error clearing draft:', e);
        }
    }

    showAutoSaveIndicator() {
        const indicator = document.getElementById('autosave-indicator') || this.createAutoSaveIndicator();
        indicator.textContent = '✓ Draft saved';
        indicator.style.opacity = '1';
        
        setTimeout(() => {
            indicator.style.opacity = '0';
        }, 2000);
    }

    createAutoSaveIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'autosave-indicator';
        indicator.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #10B981;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            transition: opacity 0.3s;
            opacity: 0;
            z-index: 9999;
        `;
        document.body.appendChild(indicator);
        return indicator;
    }

    /**
     * Poll for new notifications
     */
    setupNotificationPolling() {
        const notificationBadge = document.querySelector('.notification-badge');
        if (!notificationBadge) return;

        // Poll every 30 seconds
        setInterval(async () => {
            try {
                const response = await fetch('/forum/api/unread-notifications/', {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.unread_count > 0) {
                        notificationBadge.textContent = data.unread_count;
                        notificationBadge.style.display = 'block';
                    } else {
                        notificationBadge.style.display = 'none';
                    }
                }
            } catch (error) {
                console.error('Error polling notifications:', error);
            }
        }, 30000);
    }

    /**
     * Enhanced search with suggestions
     */
    setupSearchEnhancements() {
        const searchInput = document.querySelector('input[name="search"]');
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                // Could implement search suggestions here
                console.log('Searching for:', this.value);
            }, 300);
        });
    }

    /**
     * Keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K: Focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('input[name="search"]');
                if (searchInput) searchInput.focus();
            }

            // Ctrl/Cmd + Enter: Submit form
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const activeElement = document.activeElement;
                if (activeElement.tagName === 'TEXTAREA') {
                    const form = activeElement.closest('form');
                    if (form) form.submit();
                }
            }
        });
    }
}

/**
 * Toast notification system
 */
function showToast(title, message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
        <div class="toast-header">
            <i class='bx ${type === 'success' ? 'bx-check-circle' : type === 'error' ? 'bx-error' : 'bx-info-circle'}'></i>
            <strong>${title}</strong>
            <button type="button" class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="toast-body">${message}</div>
    `;

    const container = document.getElementById('toast-container') || createToastContainer();
    container.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `
        position: fixed;
        top: 90px;
        right: 20px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 10px;
    `;
    document.body.appendChild(container);
    return container;
}

/**
 * Get CSRF token from cookies
 */
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

/**
 * Format relative time
 */
function formatRelativeTime(date) {
    const now = new Date();
    const diff = now - new Date(date);
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return 'just now';
}

/**
 * Lazy load images
 */
function setupLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for browsers without IntersectionObserver
        images.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
    }
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes vote-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }

    .animate-vote {
        animation: vote-pulse 0.3s ease;
    }

    .toast-notification {
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        min-width: 300px;
        opacity: 1;
        transition: opacity 0.3s;
    }

    .toast-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-weight: 600;
    }

    .toast-header i {
        font-size: 20px;
    }

    .toast-success .toast-header i { color: #10B981; }
    .toast-error .toast-header i { color: #EF4444; }
    .toast-info .toast-header i { color: #3B82F6; }

    .toast-close {
        margin-left: auto;
        background: none;
        border: none;
        font-size: 24px;
        cursor: pointer;
        color: #6B7280;
    }

    .toast-body {
        color: #6B7280;
        font-size: 14px;
    }

    .content-feedback {
        animation: slideDown 0.3s ease;
    }

    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new ForumEnhancements();
        setupLazyLoading();
    });
} else {
    new ForumEnhancements();
    setupLazyLoading();
}
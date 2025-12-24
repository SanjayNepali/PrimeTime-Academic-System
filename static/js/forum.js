// File: static/js/forum.js

/**
 * Forum JavaScript Enhancements
 * Enhanced with Real-time Content Moderation
 * Integrates with backend sentiment analysis and content detection algorithms
 */

class ForumEnhancements {
    constructor() {
        // Enhanced content moderation patterns
        this.profanityWords = new Set([
            'shit', 'fuck', 'damn', 'hell', 'bitch', 'bastard', 
            'asshole', 'crap', 'piss', 'dick', 'idiot', 'stupid', 
            'dumb', 'moron', 'loser', 'nigger', 'nigga', 'chink',
            'spic', 'kike', 'retard', 'fag', 'faggot'
        ]);
        
        this.harassmentWords = new Set([
            'kill', 'die', 'death', 'hate', 'attack', 'threat', 
            'harm', 'hurt', 'destroy', 'murder', 'suicide', 'stab',
            'shoot', 'bomb', 'assault', 'rape', 'abuse'
        ]);

        this.suspiciousPatterns = [
            /\b(password|login|credentials|account)\b/i,
            /\b(free.?money|earn.?fast|make.?money|work.?from.?home)\b/i,
            /\b(click.?here|limited.?time|special.?offer)\b/i,
            /(http|https|www\.|\.[a-z]{2,})/i, // URLs
            /\b(wire.?transfer|bitcoin|crypto|paypal|bank)\b/i,
            /\d{10,}/g, // Long numbers (potential personal info)
        ];

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
        this.setupContentModeration();
    }

    /**
     * Real-time content analysis as user types
     * Provides feedback on potentially inappropriate content
     */
    setupRealTimeContentAnalysis() {
        const contentFields = document.querySelectorAll('textarea[name="content"], input[name="title"]');
        
        if (contentFields.length === 0) return;

        // Inappropriate keywords patterns
        const inappropriatePatterns = [
            /\b(spam|scam|fake|phishing|fraud)\b/i,
            /\b(cheat|plagiar|copy|steal)\b/i,
            /\b(virus|malware|hack|crack)\b/i
        ];

        contentFields.forEach(field => {
            let analysisTimeout;
            const feedbackDiv = this.createFeedbackDiv(field);

            field.addEventListener('input', () => {
                clearTimeout(analysisTimeout);
                analysisTimeout = setTimeout(() => {
                    this.analyzeContent(field.value, feedbackDiv, inappropriatePatterns, this.suspiciousPatterns);
                }, 500);
            });
        });
    }

    /**
     * Enhanced content moderation system
     */
    setupContentModeration() {
        const contentFields = document.querySelectorAll('textarea[name="content"], input[name="title"]');
        
        contentFields.forEach(field => {
            let moderationTimeout;
            
            field.addEventListener('input', () => {
                clearTimeout(moderationTimeout);
                moderationTimeout = setTimeout(() => {
                    this.checkContentModeration(field);
                }, 500);
            });
        });
    }

    checkContentModeration(field) {
        const text = field.value.toLowerCase();
        const words = text.match(/\b\w+\b/g) || [];
        
        let issues = [];
        let suggestions = [];
        let severity = 'none';

        // Check for profanity
        const foundProfanity = words.filter(word => this.profanityWords.has(word));
        if (foundProfanity.length > 0) {
            issues.push(`Profanity detected: ${foundProfanity.slice(0, 3).join(', ')}`);
            suggestions.push('Please remove profanity and use professional language');
            severity = 'high';
        }

        // Check for harassment
        const foundHarassment = words.filter(word => this.harassmentWords.has(word));
        if (foundHarassment.length > 0) {
            issues.push('Potentially threatening or harassing language detected');
            suggestions.push('Be respectful and constructive in your communication');
            severity = 'high';
        }

        // Check for hate speech patterns
        const hatePatterns = [
            /\b(all\s*(white|black|asian|jewish|muslim|gay)s?\s*(are|is)\s*(stupid|bad|evil|wrong))\b/i,
            /\b(I\s*hate\s*(all|every)\s*(white|black|asian|jewish|muslim|gay|trans))\b/i,
            /\b(die\s*(all|every)\s*(white|black|asian|jewish|muslim|gay|trans))\b/i
        ];
        
        hatePatterns.forEach(pattern => {
            if (pattern.test(text)) {
                issues.push('Hate speech detected');
                suggestions.push('Hate speech is strictly prohibited. Please review community guidelines.');
                severity = 'high';
            }
        });

        // Check for excessive caps
        if (text.length > 20) {
            const capsRatio = (text.match(/[A-Z]/g) || []).length / text.length;
            if (capsRatio > 0.7) {
                issues.push('Excessive use of capital letters (appears to be yelling)');
                suggestions.push('Use normal case for better readability');
                severity = severity === 'none' ? 'medium' : severity;
            }
        }

        // Check for excessive punctuation
        if ((text.match(/!/g) || []).length > 5 || (text.match(/\?/g) || []).length > 5) {
            issues.push('Too many exclamation or question marks');
            suggestions.push('Use punctuation moderately for clear communication');
            severity = severity === 'none' ? 'low' : severity;
        }

        // Check for spam patterns
        if (text.includes('$$$') || text.includes('!!!') || text.includes('???')) {
            issues.push('Spam-like patterns detected');
            suggestions.push('Avoid excessive special characters');
            severity = severity === 'none' ? 'medium' : severity;
        }

        // Check for repeated words
        const wordCounts = {};
        words.forEach(word => {
            wordCounts[word] = (wordCounts[word] || 0) + 1;
        });
        
        const repeatedWords = Object.entries(wordCounts).filter(([word, count]) => count > 5);
        if (repeatedWords.length > 0) {
            issues.push(`Repeated words detected (${repeatedWords.map(([w]) => w).join(', ')})`);
            suggestions.push('Avoid repeating the same words multiple times');
            severity = severity === 'none' ? 'low' : severity;
        }

        // Display moderation feedback
        this.displayModerationFeedback(field, issues, suggestions, severity);
    }

    displayModerationFeedback(field, issues, suggestions, severity) {
        // Remove existing moderation feedback
        const existingFeedback = field.parentElement.querySelector('.content-moderation-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }

        if (issues.length === 0 && suggestions.length === 0) {
            return;
        }

        // Create feedback element
        const feedback = document.createElement('div');
        feedback.className = `content-moderation-feedback alert mt-2 ${severity === 'high' ? 'alert-danger' : severity === 'medium' ? 'alert-warning' : 'alert-info'}`;
        
        let html = '';
        
        if (issues.length > 0) {
            html += '<strong><i class="bx bx-error"></i> Content Issues:</strong><ul class="mb-1">';
            issues.forEach(issue => {
                html += `<li>${issue}</li>`;
            });
            html += '</ul>';
        }
        
        if (suggestions.length > 0) {
            html += '<strong class="d-block mt-2"><i class="bx bx-info-circle"></i> Suggestions:</strong><ul class="mb-0">';
            suggestions.forEach(suggestion => {
                html += `<li>${suggestion}</li>`;
            });
            html += '</ul>';
        }
        
        feedback.innerHTML = html;
        field.parentElement.appendChild(feedback);

        // Disable submit if severe issues
        const form = field.closest('form');
        const submitBtn = form?.querySelector('button[type="submit"]');
        if (submitBtn && severity === 'high') {
            submitBtn.disabled = true;
            submitBtn.title = 'Content contains prohibited language';
            submitBtn.innerHTML = '<i class="bx bx-block"></i> Content Blocked';
            submitBtn.classList.remove('btn-primary');
            submitBtn.classList.add('btn-danger');
        } else if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.title = '';
            submitBtn.classList.remove('btn-danger');
            submitBtn.classList.add('btn-primary');
            const originalText = submitBtn.dataset.originalText || submitBtn.innerHTML;
            submitBtn.dataset.originalText = originalText;
            submitBtn.innerHTML = originalText.includes('Create') ? '<i class="bx bx-send"></i> Create Post' : '<i class="bx bx-send"></i> Post Reply';
        }
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

        // Check for very short content
        if (text.length < 20 && text.split(' ').length < 5) {
            issues.push({
                type: 'warning',
                message: 'Content appears very short. Consider adding more details.'
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
                            showToast('Success', 'Post upvoted!', 'success');
                        } else {
                            this.classList.remove('btn-primary');
                            this.classList.add('btn-outline-primary');
                            showToast('Success', 'Upvote removed', 'info');
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
                    showToast('Error', 'Failed to upvote reply', 'error');
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
                showToast('Draft Restored', 'Your draft has been loaded. Remember to save!', 'info');
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

        // Warn before leaving if there's a draft
        window.addEventListener('beforeunload', (e) => {
            const draft = this.loadDraft(AUTOSAVE_KEY);
            if (draft && (draft.title || draft.content)) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            }
        });
    }

    saveDraft(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
        } catch (e) {
            console.error('Error saving draft:', e);
            showToast('Error', 'Failed to save draft', 'error');
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
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
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

        // Initial check
        this.checkNotifications(notificationBadge);

        // Poll every 30 seconds
        setInterval(() => {
            this.checkNotifications(notificationBadge);
        }, 30000);
    }

    async checkNotifications(notificationBadge) {
        try {
            const response = await fetch('/forum/api/unread-notifications/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.unread_count > 0) {
                    notificationBadge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
                    notificationBadge.style.display = 'block';
                    
                    // Show notification alert if new notifications
                    if (data.new_notifications && data.new_notifications.length > 0) {
                        data.new_notifications.forEach(notification => {
                            showToast('New Notification', notification.message, 'info');
                        });
                    }
                } else {
                    notificationBadge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error polling notifications:', error);
        }
    }

    /**
     * Enhanced search with suggestions
     */
    setupSearchEnhancements() {
        const searchInput = document.querySelector('input[name="search"]');
        if (!searchInput) return;

        let searchTimeout;
        const suggestionsContainer = this.createSearchSuggestions(searchInput);

        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            suggestionsContainer.style.display = 'none';
            
            if (this.value.length < 2) return;
            
            searchTimeout = setTimeout(async () => {
                try {
                    const response = await fetch(`/forum/api/search-suggestions/?q=${encodeURIComponent(this.value)}`, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    
                    if (response.ok) {
                        const suggestions = await response.json();
                        if (suggestions.length > 0) {
                            suggestionsContainer.innerHTML = suggestions.map(suggestion => 
                                `<div class="search-suggestion" data-suggestion="${suggestion}">
                                    <i class="bx bx-search"></i> ${suggestion}
                                </div>`
                            ).join('');
                            suggestionsContainer.style.display = 'block';
                        }
                    }
                } catch (error) {
                    console.error('Error fetching suggestions:', error);
                }
            }, 300);
        });

        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                suggestionsContainer.style.display = 'none';
            }
        });
    }

    createSearchSuggestions(searchInput) {
        const container = document.createElement('div');
        container.className = 'search-suggestions';
        container.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            display: none;
            max-height: 300px;
            overflow-y: auto;
        `;
        
        searchInput.parentElement.style.position = 'relative';
        searchInput.parentElement.appendChild(container);
        
        return container;
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
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }

            // Ctrl/Cmd + Enter: Submit form
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const activeElement = document.activeElement;
                if (activeElement.tagName === 'TEXTAREA' || activeElement.tagName === 'INPUT') {
                    const form = activeElement.closest('form');
                    if (form && !activeElement.disabled) {
                        e.preventDefault();
                        form.submit();
                    }
                }
            }

            // Escape: Close modals, clear search
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.modal.show');
                if (activeModal) {
                    const closeBtn = activeModal.querySelector('[data-bs-dismiss="modal"]');
                    if (closeBtn) closeBtn.click();
                }
                
                const searchInput = document.querySelector('input[name="search"]');
                if (document.activeElement === searchInput && searchInput.value) {
                    searchInput.value = '';
                    searchInput.dispatchEvent(new Event('input'));
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

    // Add slide-in animation
    toast.style.animation = 'slideInRight 0.3s ease-out';

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
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
                    if (img.dataset.srcset) {
                        img.srcset = img.dataset.srcset;
                    }
                    img.classList.add('fade-in');
                    img.removeAttribute('data-src');
                    img.removeAttribute('data-srcset');
                    imageObserver.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px 0px',
            threshold: 0.1
        });

        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for browsers without IntersectionObserver
        images.forEach(img => {
            img.src = img.dataset.src;
            if (img.dataset.srcset) {
                img.srcset = img.dataset.srcset;
            }
            img.removeAttribute('data-src');
            img.removeAttribute('data-srcset');
        });
    }
}

// Add CSS for animations and styles
const style = document.createElement('style');
style.textContent = `
    @keyframes vote-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }

    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
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
        transition: all 0.3s ease;
        border-left: 4px solid #3B82F6;
    }

    .toast-notification.toast-success {
        border-left-color: #10B981;
    }

    .toast-notification.toast-error {
        border-left-color: #EF4444;
    }

    .toast-notification.toast-info {
        border-left-color: #3B82F6;
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
        line-height: 1;
        padding: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .toast-body {
        color: #6B7280;
        font-size: 14px;
    }

    .content-feedback {
        animation: slideDown 0.3s ease;
    }

    .content-moderation-feedback {
        animation: slideDown 0.3s ease;
    }

    .content-moderation-feedback ul {
        margin-bottom: 0.5rem;
        padding-left: 1.5rem;
    }

    .content-moderation-feedback li {
        margin-bottom: 0.25rem;
        font-size: 0.9rem;
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

    .fade-in {
        animation: fadeIn 0.5s ease-in;
    }

    .search-suggestion {
        padding: 10px 15px;
        cursor: pointer;
        transition: background-color 0.2s;
        border-bottom: 1px solid #f0f0f0;
    }

    .search-suggestion:last-child {
        border-bottom: none;
    }

    .search-suggestion:hover {
        background-color: #f5f5f5;
    }

    .search-suggestion i {
        margin-right: 8px;
        color: #666;
    }

    .btn-danger:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .btn-success:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .btn-primary:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .notification-badge {
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.1);
        }
        100% {
            transform: scale(1);
        }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const forumEnhancements = new ForumEnhancements();
        setupLazyLoading();
        
        // Make forumEnhancements available globally for debugging
        window.forumEnhancements = forumEnhancements;
    });
} else {
    const forumEnhancements = new ForumEnhancements();
    setupLazyLoading();
    window.forumEnhancements = forumEnhancements;
}

// Export utility functions for use in other modules
window.ForumUtils = {
    showToast,
    getCookie,
    formatRelativeTime,
    setupLazyLoading
};
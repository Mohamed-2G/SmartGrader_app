// SmartGrader - Main JavaScript File

// ===== UTILITY FUNCTIONS =====
const SmartGrader = {
    // Show notification
    showNotification: function(message, type = 'info') {
        const alertClass = `alert-${type}`;
        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Insert at top of main content
        const mainContent = document.querySelector('.main-content') || document.querySelector('.container');
        if (mainContent) {
            mainContent.insertAdjacentHTML('afterbegin', alertHtml);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                const alert = mainContent.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, 5000);
        }
    },

    // Show loading spinner
    showLoading: function(container) {
        const spinner = `
            <div class="spinner" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        `;
        container.innerHTML = spinner;
    },

    // Hide loading spinner
    hideLoading: function(container, content) {
        container.innerHTML = content;
    },

    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Validate file type
    validateFileType: function(file, allowedTypes) {
        return allowedTypes.includes(file.type);
    },

    // Validate file size
    validateFileSize: function(file, maxSize) {
        return file.size <= maxSize;
    }
};

// ===== FILE UPLOAD HANDLING =====
class FileUploadHandler {
    constructor(dropZone, fileInput, allowedTypes = [], maxSize = 10 * 1024 * 1024) {
        this.dropZone = dropZone;
        this.fileInput = fileInput;
        this.allowedTypes = allowedTypes;
        this.maxSize = maxSize;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateDropZoneText();
    }

    setupEventListeners() {
        // Drag and drop events
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('dragover');
        });

        this.dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
        });

        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFiles(files);
            }
        });

        // File input change
        this.fileInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files.length > 0) {
                this.handleFiles(files);
            }
        });

        // Click to upload
        this.dropZone.addEventListener('click', () => {
            this.fileInput.click();
        });
    }

    handleFiles(files) {
        const file = files[0]; // Handle first file only
        
        // Validate file type
        if (this.allowedTypes.length > 0 && !SmartGrader.validateFileType(file, this.allowedTypes)) {
            SmartGrader.showNotification(`Invalid file type. Allowed types: ${this.allowedTypes.join(', ')}`, 'danger');
            return;
        }

        // Validate file size
        if (!SmartGrader.validateFileSize(file, this.maxSize)) {
            SmartGrader.showNotification(`File too large. Maximum size: ${SmartGrader.formatFileSize(this.maxSize)}`, 'danger');
            return;
        }

        // Update display
        this.updateFileDisplay(file);
        
        // Trigger form submission if needed
        this.triggerFormSubmission(file);
    }

    updateFileDisplay(file) {
        const fileInfo = `
            <div class="file-info">
                <i class="fas fa-file"></i>
                <span class="file-name">${file.name}</span>
                <span class="file-size">(${SmartGrader.formatFileSize(file.size)})</span>
            </div>
        `;
        this.dropZone.innerHTML = fileInfo;
    }

    updateDropZoneText() {
        if (!this.dropZone.querySelector('.file-info')) {
            this.dropZone.innerHTML = `
                <i class="fas fa-cloud-upload-alt fa-3x mb-3"></i>
                <p>Drag and drop files here or click to browse</p>
                <small class="text-muted">
                    Max size: ${SmartGrader.formatFileSize(this.maxSize)}
                    ${this.allowedTypes.length > 0 ? `<br>Allowed types: ${this.allowedTypes.join(', ')}` : ''}
                </small>
            `;
        }
    }

    triggerFormSubmission(file) {
        // Find the form and submit it
        const form = this.fileInput.closest('form');
        if (form) {
            // Add a small delay to show the file info
            setTimeout(() => {
                form.submit();
            }, 1000);
        }
    }
}

// ===== DYNAMIC FORM HANDLING =====
class DynamicFormHandler {
    constructor(container, addButton, removeButtonClass = 'remove-question') {
        this.container = container;
        this.addButton = addButton;
        this.removeButtonClass = removeButtonClass;
        this.questionCounter = 1;
        this.init();
    }

    init() {
        this.addButton.addEventListener('click', () => this.addQuestion());
        this.setupRemoveListeners();
    }

    addQuestion() {
        this.questionCounter++;
        const questionHtml = this.createQuestionHtml(this.questionCounter);
        this.container.insertAdjacentHTML('beforeend', questionHtml);
        this.setupRemoveListeners();
    }

    createQuestionHtml(counter) {
        return `
            <div class="question-group card mb-3" data-question="${counter}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Question ${counter}</h6>
                    <button type="button" class="btn btn-danger btn-sm ${this.removeButtonClass}">
                        <i class="fas fa-trash"></i> Remove
                    </button>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">Question Text</label>
                        <textarea class="form-control" name="question_${counter}" rows="3" required></textarea>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <label class="form-label">Points</label>
                            <input type="number" class="form-control" name="points_${counter}" min="1" max="100" value="10" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Question Type</label>
                            <select class="form-control" name="type_${counter}">
                                <option value="essay">Essay</option>
                                <option value="short_answer">Short Answer</option>
                                <option value="multiple_choice">Multiple Choice</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupRemoveListeners() {
        const removeButtons = this.container.querySelectorAll(`.${this.removeButtonClass}`);
        removeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const questionGroup = e.target.closest('.question-group');
                if (questionGroup) {
                    questionGroup.remove();
                    this.renumberQuestions();
                }
            });
        });
    }

    renumberQuestions() {
        const questions = this.container.querySelectorAll('.question-group');
        questions.forEach((question, index) => {
            const counter = index + 1;
            question.dataset.question = counter;
            question.querySelector('.card-header h6').textContent = `Question ${counter}`;
            
            // Update form field names
            const textarea = question.querySelector('textarea');
            const pointsInput = question.querySelector('input[type="number"]');
            const typeSelect = question.querySelector('select');
            
            if (textarea) textarea.name = `question_${counter}`;
            if (pointsInput) pointsInput.name = `points_${counter}`;
            if (typeSelect) typeSelect.name = `type_${counter}`;
        });
        this.questionCounter = questions.length;
    }
}

// ===== MODAL HANDLING =====
class ModalHandler {
    constructor() {
        this.setupModalListeners();
    }

    setupModalListeners() {
        // Delete confirmation modals
        document.querySelectorAll('[data-bs-toggle="modal"]').forEach(button => {
            button.addEventListener('click', (e) => {
                const target = e.target.getAttribute('data-bs-target');
                const modal = document.querySelector(target);
                if (modal) {
                    const confirmButton = modal.querySelector('.btn-confirm');
                    if (confirmButton) {
                        confirmButton.addEventListener('click', () => {
                            this.handleConfirmAction(e.target);
                        });
                    }
                }
            });
        });
    }

    handleConfirmAction(button) {
        const action = button.getAttribute('data-action');
        const itemId = button.getAttribute('data-item-id');
        
        if (action === 'delete') {
            this.deleteItem(itemId, button.getAttribute('data-item-type'));
        }
    }

    async deleteItem(itemId, itemType) {
        try {
            const response = await fetch(`/instructor/${itemType}/${itemId}/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                SmartGrader.showNotification('Item deleted successfully', 'success');
                // Remove from DOM or redirect
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                SmartGrader.showNotification(result.error || 'Failed to delete item', 'danger');
            }
        } catch (error) {
            SmartGrader.showNotification('An error occurred while deleting the item', 'danger');
        }
    }
}

// ===== GRADING STATUS UPDATES =====
class GradingStatusHandler {
    constructor() {
        this.setupStatusPolling();
    }

    setupStatusPolling() {
        const statusElements = document.querySelectorAll('[data-submission-id]');
        statusElements.forEach(element => {
            const submissionId = element.dataset.submissionId;
            this.pollStatus(submissionId, element);
        });
    }

    async pollStatus(submissionId, element) {
        const maxAttempts = 60; // 5 minutes with 5-second intervals
        let attempts = 0;

        const poll = async () => {
            try {
                const response = await fetch(`/instructor/submission/${submissionId}/status`);
                const data = await response.json();
                
                if (data.success) {
                    this.updateStatusDisplay(element, data);
                    
                    if (data.status === 'completed' || data.status === 'failed') {
                        return; // Stop polling
                    }
                }
                
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, 5000); // Poll every 5 seconds
                }
            } catch (error) {
                console.error('Error polling status:', error);
            }
        };

        poll();
    }

    updateStatusDisplay(element, data) {
        const statusBadge = element.querySelector('.status-badge');
        const progressBar = element.querySelector('.progress-bar');
        
        if (statusBadge) {
            statusBadge.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
            statusBadge.className = `badge status-badge badge-${this.getStatusClass(data.status)}`;
        }
        
        if (progressBar) {
            const progress = this.getProgressPercentage(data.status);
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${progress}%`;
        }
        
        if (data.is_graded && data.total_score !== null) {
            const scoreElement = element.querySelector('.score-display');
            if (scoreElement) {
                scoreElement.textContent = `${data.total_score}/${data.max_score}`;
            }
        }
    }

    getStatusClass(status) {
        const statusClasses = {
            'pending': 'warning',
            'grading': 'info',
            'completed': 'success',
            'failed': 'danger'
        };
        return statusClasses[status] || 'secondary';
    }

    getProgressPercentage(status) {
        const progressMap = {
            'pending': 0,
            'grading': 50,
            'completed': 100,
            'failed': 100
        };
        return progressMap[status] || 0;
    }
}

// ===== FORM VALIDATION =====
class FormValidator {
    constructor(form) {
        this.form = form;
        this.init();
    }

    init() {
        this.form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
            }
        });
    }

    validateForm() {
        let isValid = true;
        const requiredFields = this.form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        const fieldName = field.name || field.id || 'Field';
        
        // Remove existing error styling
        field.classList.remove('is-invalid');
        const existingError = field.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
        
        // Check if required field is empty
        if (field.hasAttribute('required') && !value) {
            this.showFieldError(field, `${fieldName} is required`);
            return false;
        }
        
        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                this.showFieldError(field, 'Please enter a valid email address');
                return false;
            }
        }
        
        // File validation
        if (field.type === 'file' && field.files.length > 0) {
            const file = field.files[0];
            const maxSize = field.dataset.maxSize || 10 * 1024 * 1024; // 10MB default
            
            if (file.size > maxSize) {
                this.showFieldError(field, `File size must be less than ${SmartGrader.formatFileSize(maxSize)}`);
                return false;
            }
        }
        
        return true;
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    // Initialize file upload handlers
    document.querySelectorAll('.file-upload').forEach(dropZone => {
        const fileInput = dropZone.querySelector('input[type="file"]');
        if (fileInput) {
            new FileUploadHandler(dropZone, fileInput);
        }
    });

    // Initialize dynamic forms
    document.querySelectorAll('.dynamic-form').forEach(container => {
        const addButton = container.querySelector('.add-question');
        if (addButton) {
            new DynamicFormHandler(container, addButton);
        }
    });

    // Initialize modal handlers
    new ModalHandler();

    // Initialize grading status handlers
    new GradingStatusHandler();

    // Initialize form validators
    document.querySelectorAll('form').forEach(form => {
        new FormValidator(form);
    });

    // Add fade-in animation to cards
    document.querySelectorAll('.card').forEach(card => {
        card.classList.add('fade-in');
    });

    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });
});

// ===== GLOBAL EVENT LISTENERS =====
document.addEventListener('click', function(e) {
    // Handle delete buttons
    if (e.target.classList.contains('btn-delete')) {
        if (!confirm('Are you sure you want to delete this item?')) {
            e.preventDefault();
        }
    }
    
    // Handle copy to clipboard
    if (e.target.classList.contains('btn-copy')) {
        const textToCopy = e.target.dataset.copy;
        if (textToCopy) {
            navigator.clipboard.writeText(textToCopy).then(() => {
                SmartGrader.showNotification('Copied to clipboard!', 'success');
            });
        }
    }
});

// Export for use in other scripts
window.SmartGrader = SmartGrader;

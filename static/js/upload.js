// Allowed file extensions and MIME types
const ALLOWED_EXTENSIONS = ['.csv', '.xls', '.xlsx', '.ods', '.tsv'];
const ALLOWED_MIME_TYPES = [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.oasis.opendocument.spreadsheet',
    'text/tab-separated-values'
];

const MIME_TO_EXTS = {
    'text/csv': ['.csv'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.oasis.opendocument.spreadsheet': ['.ods'],
    'text/tab-separated-values': ['.tsv']
};

// Get DOM elements
const uploadForm = document.getElementById('uploadForm');
const emailInput = document.getElementById('email');
const fileInput = document.getElementById('file');
const fileLabel = document.querySelector('.file-label');
const fileName = document.getElementById('fileName');
const emailError = document.getElementById('emailError');
const fileError = document.getElementById('fileError');
const submitBtn = document.getElementById('submitBtn');
const btnText = document.getElementById('btnText');
const btnLoader = document.getElementById('btnLoader');
const resultContainer = document.getElementById('resultContainer');

// File input change handler
fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    
    if (file) {
        fileName.textContent = file.name;
        fileLabel.classList.add('active');
        validateFile(file);
    } else {
        fileName.textContent = 'Choose a file...';
        fileLabel.classList.remove('active');
        fileError.textContent = '';
    }
});

// Email validation
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

emailInput.addEventListener('blur', function() {
    const email = emailInput.value.trim();
    
    if (!email) {
        emailError.textContent = 'Email is required';
        emailInput.classList.add('error');
    } else if (!validateEmail(email)) {
        emailError.textContent = 'Please enter a valid email address';
        emailInput.classList.add('error');
    } else {
        emailError.textContent = '';
        emailInput.classList.remove('error');
    }
});

emailInput.addEventListener('input', function() {
    if (emailError.textContent) {
        emailInput.classList.remove('error');
        emailError.textContent = '';
    }
});

// File validation
function validateFile(file) {
    fileError.textContent = '';
    
    // Check if file is empty
    if (file.size === 0) {
        fileError.textContent = 'File is empty. Please select a valid file.';
        return false;
    }
    
    // Check file extension
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(fileExt)) {
        fileError.textContent = `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`;
        return false;
    }
    
    // Check MIME type
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
        fileError.textContent = `Invalid file format. Detected: ${file.type || 'unknown'}`;
        return false;
    }
    
    // Check if extension matches MIME type
    const validExtsForMime = MIME_TO_EXTS[file.type] || [];
    if (!validExtsForMime.includes(fileExt)) {
        fileError.textContent = `File extension '${fileExt}' doesn't match file type '${file.type}'`;
        return false;
    }
    
    // Check file size (max 50MB)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
        fileError.textContent = 'File is too large. Maximum size is 50MB.';
        return false;
    }
    
    return true;
}

// Form submission
uploadForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Validate email
    const email = emailInput.value.trim();
    if (!email || !validateEmail(email)) {
        emailError.textContent = 'Please enter a valid email address';
        emailInput.classList.add('error');
        emailInput.focus();
        return;
    }
    
    // Validate file
    const file = fileInput.files[0];
    if (!file) {
        fileError.textContent = 'Please select a file';
        return;
    }
    
    if (!validateFile(file)) {
        return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('email', email);
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline-block';
    
    try {
        // Send request
        const response = await fetch('/api/v1/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showResult('success', data);
        } else {
            showResult('error', data);
        }
    } catch (error) {
        showResult('error', { 
            message: 'Network error. Please check your connection and try again.',
            detail: error.message 
        });
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
});

// Show result
function showResult(type, data) {
    const resultIcon = document.getElementById('resultIcon');
    const resultTitle = document.getElementById('resultTitle');
    const resultMessage = document.getElementById('resultMessage');
    const taskInfo = document.getElementById('taskInfo');
    const taskId = document.getElementById('taskId');
    const taskEmail = document.getElementById('taskEmail');
    
    uploadForm.style.display = 'none';
    resultContainer.style.display = 'block';
    
    if (type === 'success') {
        resultIcon.textContent = '✅';
        resultTitle.textContent = 'Upload Successful!';
        resultMessage.textContent = data.message || 'Your file has been uploaded and is being processed.';
        
        if (data.task_id) {
            taskInfo.style.display = 'block';
            taskId.textContent = data.task_id;
            taskEmail.textContent = data.email;
        }
    } else {
        resultIcon.textContent = '❌';
        resultTitle.textContent = 'Upload Failed';
        resultMessage.textContent = data.detail || data.message || 'An error occurred while uploading your file.';
        taskInfo.style.display = 'none';
    }
}

// Reset form
function resetForm() {
    uploadForm.reset();
    fileName.textContent = 'Choose a file...';
    fileLabel.classList.remove('active');
    emailError.textContent = '';
    fileError.textContent = '';
    emailInput.classList.remove('error');
    
    uploadForm.style.display = 'block';
    resultContainer.style.display = 'none';
}

// Drag and drop support
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    fileLabel.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    fileLabel.addEventListener(eventName, () => {
        fileLabel.classList.add('active');
    });
});

['dragleave', 'drop'].forEach(eventName => {
    fileLabel.addEventListener(eventName, () => {
        fileLabel.classList.remove('active');
    });
});

fileLabel.addEventListener('drop', function(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    
    if (files.length > 0) {
        fileInput.files = files;
        const event = new Event('change', { bubbles: true });
        fileInput.dispatchEvent(event);
    }
});
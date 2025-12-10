// State management
let selectedFile = null;

// DOM elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const clearBtn = document.getElementById('clearBtn');
const convertBtn = document.getElementById('convertBtn');
const progressSection = document.getElementById('progressSection');
const alertContainer = document.getElementById('alertContainer');
const downloadSection = document.getElementById('downloadSection');
const downloadLink = document.getElementById('downloadLink');

// Constants
const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.epub'];
const API_ENDPOINT = '/api/convert';

// Initialize event listeners
function init() {
    // Drop zone events
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleDrop);
    
    // Keyboard accessibility for drop zone
    dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInput.click();
        }
    });
    
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Browse button
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });
    
    // Clear button
    clearBtn.addEventListener('click', clearFile);
    
    // Convert button
    convertBtn.addEventListener('click', handleConvert);
}

// Drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

// File selection handler
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

// Process and validate file
function processFile(file) {
    // Clear previous alerts and downloads
    clearAlerts();
    hideDownload();
    
    // Validate file extension
    const fileExtension = getFileExtension(file.name);
    if (!ALLOWED_EXTENSIONS.includes(fileExtension)) {
        showError(`Invalid file type. Please upload an EPUB file.`);
        return;
    }
    
    // Validate file size
    if (file.size > MAX_FILE_SIZE_BYTES) {
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        showError(`File size (${fileSizeMB} MB) exceeds maximum allowed size of ${MAX_FILE_SIZE_MB} MB.`);
        return;
    }
    
    // File is valid
    selectedFile = file;
    displayFileInfo(file);
    convertBtn.disabled = false;
}

// Display file information
function displayFileInfo(file) {
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.classList.remove('d-none');
}

// Clear selected file
function clearFile() {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.classList.add('d-none');
    convertBtn.disabled = true;
    clearAlerts();
    hideDownload();
}

// Handle conversion
async function handleConvert() {
    if (!selectedFile) {
        showError('Please select a file first.');
        return;
    }
    
    // Disable UI during conversion
    convertBtn.disabled = true;
    clearBtn.disabled = true;
    dropZone.style.pointerEvents = 'none';
    
    // Show progress indicator
    showProgress();
    clearAlerts();
    hideDownload();
    
    try {
        // Create form data
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        // Send request to API
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            body: formData,
        });
        
        // Handle response
        if (response.ok) {
            // Success - handle PDF blob
            const blob = await response.blob();
            const outputFilename = getOutputFilename(selectedFile.name);
            
            // Create download link
            const url = URL.createObjectURL(blob);
            downloadLink.href = url;
            downloadLink.download = outputFilename;
            
            // Show success and download section
            hideProgress();
            showDownload();
            showSuccess('Conversion completed successfully!');
        } else {
            // Error - try to parse JSON error
            let errorMessage = 'Conversion failed. Please try again.';
            
            try {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.detail || errorMessage;
                } else {
                    const errorText = await response.text();
                    if (errorText) {
                        errorMessage = errorText;
                    }
                }
            } catch (parseError) {
                console.error('Error parsing error response:', parseError);
            }
            
            hideProgress();
            showError(errorMessage);
        }
    } catch (error) {
        console.error('Conversion error:', error);
        hideProgress();
        showError('Network error. Please check your connection and try again.');
    } finally {
        // Re-enable UI
        convertBtn.disabled = false;
        clearBtn.disabled = false;
        dropZone.style.pointerEvents = 'auto';
    }
}

// UI helper functions
function showProgress() {
    progressSection.classList.remove('d-none');
}

function hideProgress() {
    progressSection.classList.add('d-none');
}

function showDownload() {
    downloadSection.classList.remove('d-none');
}

function hideDownload() {
    downloadSection.classList.add('d-none');
}

function clearAlerts() {
    alertContainer.innerHTML = '';
}

function showError(message) {
    const alert = createAlert('danger', message, 'bi-exclamation-triangle-fill');
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alert);
}

function showSuccess(message) {
    const alert = createAlert('success', message, 'bi-check-circle-fill');
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alert);
}

function createAlert(type, message, iconClass) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} d-flex align-items-center`;
    alert.setAttribute('role', 'alert');
    
    alert.innerHTML = `
        <i class="bi ${iconClass} fs-5 me-3"></i>
        <div>${message}</div>
    `;
    
    return alert;
}

// Utility functions
function getFileExtension(filename) {
    return '.' + filename.split('.').pop().toLowerCase();
}

function getOutputFilename(inputFilename) {
    const baseName = inputFilename.replace(/\.[^/.]+$/, '');
    return `${baseName}.pdf`;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

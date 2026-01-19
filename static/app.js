// Safe Journalist Frontend

// DOM Elements
const entryForm = document.getElementById('entryForm');
const entryText = document.getElementById('entryText');
const submitBtn = document.getElementById('submitBtn');
const entryMessage = document.getElementById('entryMessage');
const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const audioMessage = document.getElementById('audioMessage');
const actionMessage = document.getElementById('actionMessage');
const refreshStatusBtn = document.getElementById('refreshStatusBtn');
const viewAlertBtn = document.getElementById('viewAlertBtn');
const manualSummarizeBtn = document.getElementById('manualSummarizeBtn');
const alertSection = document.getElementById('alertSection');
const alertContent = document.getElementById('alertContent');
const alertTimestamp = document.getElementById('alertTimestamp');
const recentEntries = document.getElementById('recentEntries');

// Status display elements
const totalEntries = document.getElementById('totalEntries');
const totalSummaries = document.getElementById('totalSummaries');
const entriesSinceLastSummary = document.getElementById('entriesSinceLastSummary');
const triggerInfo = document.getElementById('triggerInfo');

// Utility Functions
function showMessage(element, message, type = 'success') {
    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = 'block';

    // Keep errors visible until next action.
    if (type === 'error') {
        return;
    }

    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

function formatTimestamp(timestamp) {
    // Convert 20260117T123456Z to readable format
    const year = timestamp.substring(0, 4);
    const month = timestamp.substring(4, 6);
    const day = timestamp.substring(6, 8);
    const hour = timestamp.substring(9, 11);
    const minute = timestamp.substring(11, 13);
    const second = timestamp.substring(13, 15);
    
    return `${year}-${month}-${day} ${hour}:${minute}:${second} UTC`;
}

// API Functions
async function submitEntry(text) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';
    
    try {
        const response = await fetch('/entries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to submit entry');
        }
        
        const data = await response.json();
        showMessage(entryMessage, '✓ Entry submitted successfully!', 'success');
        entryText.value = '';
        
        // Auto-refresh status and entries
        await refreshStatus();
        await loadRecentEntries();
        
        return data;
    } catch (error) {
        showMessage(entryMessage, `✗ Error: ${error.message}`, 'error');
        throw error;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Entry';
    }
}

async function submitAudioBlob(blob, filename = 'recording.webm') {
    stopBtn.disabled = true;
    stopBtn.textContent = 'Sending...';

    try {
        const formData = new FormData();
        formData.append('file', blob, filename);

        const response = await fetch('/entries/audio', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            const detail = error.detail;
            if (typeof detail === 'string') {
                throw new Error(detail);
            }
            if (detail && typeof detail === 'object') {
                const msg = detail.error || JSON.stringify(detail);
                throw new Error(msg);
            }
            throw new Error('Failed to transcribe audio');
        }

        await response.json();
        showMessage(audioMessage, '✓ Audio transcribed and saved!', 'success');

        await refreshStatus();
        await loadRecentEntries();
    } catch (error) {
        showMessage(audioMessage, `✗ Error: ${error.message}`, 'error');
        throw error;
    } finally {
        stopBtn.disabled = false;
        stopBtn.textContent = 'Stop & Send';
    }
}

async function refreshStatus() {
    try {
        const response = await fetch('/status');
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }
        
        const data = await response.json();
        
        totalEntries.textContent = data.entries;
        totalSummaries.textContent = data.summaries;
        entriesSinceLastSummary.textContent = data.entries_since_last_summary;
        
        // Update trigger info
        const remaining = data.trigger_count - data.entries_since_last_summary;
        if (remaining > 0) {
            triggerInfo.textContent = `(${remaining} more until auto-summarize)`;
            triggerInfo.className = 'trigger-info pending';
        } else {
            triggerInfo.textContent = '(will trigger on next entry)';
            triggerInfo.className = 'trigger-info ready';
        }
        
        return data;
    } catch (error) {
        console.error('Failed to refresh status:', error);
    }
}

async function viewAlert() {
    viewAlertBtn.disabled = true;
    viewAlertBtn.textContent = 'Loading...';
    
    try {
        const response = await fetch('/alert');
        
        if (response.status === 404) {
            showMessage(actionMessage, 'ℹ No summary available yet. Create more entries first.', 'info');
            alertSection.style.display = 'none';
            return;
        }
        
        if (!response.ok) {
            throw new Error('Failed to fetch alert');
        }
        
        const data = await response.json();
        
        // Display alert
        alertContent.innerHTML = formatSummary(data.summary);
        alertTimestamp.textContent = `Generated: ${formatTimestamp(data.timestamp)}`;
        alertSection.style.display = 'block';
        
        // Scroll to alert
        alertSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        showMessage(actionMessage, '✓ Alert loaded successfully', 'success');
    } catch (error) {
        showMessage(actionMessage, `✗ Error: ${error.message}`, 'error');
        alertSection.style.display = 'none';
    } finally {
        viewAlertBtn.disabled = false;
        viewAlertBtn.textContent = 'View Latest Alert';
    }
}

async function triggerSummarize() {
    manualSummarizeBtn.disabled = true;
    manualSummarizeBtn.textContent = 'Triggering...';
    
    try {
        const response = await fetch('/summarize', {
            method: 'POST',
        });
        
        if (!response.ok) {
            throw new Error('Failed to trigger summarization');
        }
        
        const data = await response.json();
        
        if (data.status === 'no_entries') {
            showMessage(actionMessage, 'ℹ No entries to summarize yet', 'info');
        } else {
            showMessage(actionMessage, '✓ Summarization started in background', 'success');
        }
    } catch (error) {
        showMessage(actionMessage, `✗ Error: ${error.message}`, 'error');
    } finally {
        manualSummarizeBtn.disabled = false;
        manualSummarizeBtn.textContent = 'Manual Summarize';
    }
}

async function loadRecentEntries() {
    try {
        const response = await fetch('/entries?limit=5');
        if (!response.ok) {
            throw new Error('Failed to load entries');
        }
        
        const entries = await response.json();
        
        if (entries.length === 0) {
            recentEntries.innerHTML = '<p class="empty-state">No entries yet</p>';
            return;
        }
        
        // Build entries HTML
        const entriesHtml = entries.map(entry => `
            <div class="entry-item">
                <div class="entry-timestamp">${formatTimestamp(entry.timestamp)}</div>
                <div class="entry-preview">${escapeHtml(entry.preview)}</div>
            </div>
        `).join('');
        
        recentEntries.innerHTML = entriesHtml;
    } catch (error) {
        console.error('Failed to load entries:', error);
        recentEntries.innerHTML = '<p class="error-state">Failed to load entries</p>';
    }
}

// Utility: Format summary (convert line breaks to HTML)
function formatSummary(text) {
    return escapeHtml(text)
        .split('\n')
        .map(line => {
            // Check if line starts with bullet point or number
            if (line.trim().match(/^[-*•]\s/)) {
                return `<li>${line.trim().substring(2)}</li>`;
            } else if (line.trim().match(/^\d+\.\s/)) {
                return `<li>${line.trim().replace(/^\d+\.\s/, '')}</li>`;
            } else if (line.trim()) {
                return `<p>${line}</p>`;
            }
            return '';
        })
        .join('');
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event Listeners
entryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const text = entryText.value.trim();
    if (!text) {
        showMessage(entryMessage, '✗ Please enter some text', 'error');
        return;
    }
    
    await submitEntry(text);
});

let mediaRecorder = null;
let recordedChunks = [];

recordBtn.addEventListener('click', async () => {
    try {
        recordBtn.disabled = true;
        showMessage(audioMessage, 'Requesting microphone permission...', 'info');

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        recordedChunks = [];
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.addEventListener('dataavailable', (event) => {
            if (event.data && event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        });

        mediaRecorder.addEventListener('stop', async () => {
            // Stop tracks so the browser releases the mic.
            stream.getTracks().forEach((t) => t.stop());

            const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            const filename = `recording.${(blob.type.split('/')[1] || 'webm').split(';')[0]}`;
            await submitAudioBlob(blob, filename);
        });

        mediaRecorder.start();
        showMessage(audioMessage, 'Recording… tap “Stop & Send” when done.', 'info');

        recordBtn.textContent = 'Recording…';
        stopBtn.disabled = false;
    } catch (error) {
        showMessage(audioMessage, `✗ Mic error: ${error.message || error}`, 'error');
        recordBtn.disabled = false;
    }
});

stopBtn.addEventListener('click', () => {
    if (!mediaRecorder || mediaRecorder.state !== 'recording') {
        showMessage(audioMessage, '✗ Not recording', 'error');
        return;
    }

    stopBtn.disabled = true;
    mediaRecorder.stop();

    recordBtn.disabled = false;
    recordBtn.textContent = 'Start Recording';
});

refreshStatusBtn.addEventListener('click', async () => {
    refreshStatusBtn.disabled = true;
    refreshStatusBtn.textContent = 'Refreshing...';
    
    await refreshStatus();
    
    refreshStatusBtn.disabled = false;
    refreshStatusBtn.textContent = 'Refresh Status';
});

viewAlertBtn.addEventListener('click', viewAlert);
manualSummarizeBtn.addEventListener('click', triggerSummarize);

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await refreshStatus();
    await loadRecentEntries();
});

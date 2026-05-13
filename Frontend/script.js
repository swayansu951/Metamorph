const API_BASE_URL = 'https://armed-component-cartridge.ngrok-free.dev';
const REQUEST_HEADERS = API_BASE_URL.includes('ngrok-free.dev')
    ? { 'ngrok-skip-browser-warning': 'true' }
    : {};

const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const uploadBtn = document.getElementById('upload-btn');
const pdfFileInput = document.getElementById('pdf-file');
const docIdInput = document.getElementById('doc-id');
const statusText = document.getElementById('status-text');
const reviewPopup = document.getElementById('review-popup');
const reviewerNameInput = document.getElementById('reviewer-name');
const reviewFeedbackInput = document.getElementById('review-feedback');
const submitReviewBtn = document.getElementById('submit-review-btn');
const skipReviewBtn = document.getElementById('skip-review-btn');
const reviewStatus = document.getElementById('review-status');
const ratingButtons = Array.from(document.querySelectorAll('.rating-btn'));
const reviewTagInputs = Array.from(document.querySelectorAll('.review-tags input[type="checkbox"]'));

const REVIEWER_NAME_KEY = 'metamorph-reviewer-name';

let isSending = false;
let isUploading = false;
let isReviewSubmitting = false;
let selectedRating = 0;
let latestReviewContext = null;
let hasShownFirstReviewPopup = false;
let hasResolvedFirstReview = false;

function createRequestHeaders(extraHeaders = {}) {
    return { ...REQUEST_HEADERS, ...extraHeaders };
}

function appendMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    msgDiv.textContent = text;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msgDiv;
}

function setStatus(message, isError = false) {
    statusText.textContent = message;
    statusText.style.color = '#3A2D28';
    statusText.style.fontWeight = isError ? '700' : '400';
}

function updateButtonState() {
    sendBtn.disabled = isSending;
    uploadBtn.disabled = isUploading;
    submitReviewBtn.disabled = isReviewSubmitting || !isReviewPopupVisible();
    skipReviewBtn.disabled = isReviewSubmitting || !isReviewPopupVisible();
}

function isReviewPopupVisible() {
    return !reviewPopup.classList.contains('hidden');
}

function setReviewStatus(message, isError = false) {
    reviewStatus.textContent = message;
    reviewStatus.style.color = isError ? '#5F1C14' : '#3A2D28';
    reviewStatus.style.fontWeight = isError ? '700' : '400';
}

function setSelectedRating(rating) {
    selectedRating = rating;

    ratingButtons.forEach((button) => {
        const isActive = Number(button.dataset.rating) === rating;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-pressed', String(isActive));
    });
}

function resetReviewForm() {
    setSelectedRating(0);
    reviewFeedbackInput.value = '';
    reviewTagInputs.forEach((input) => {
        input.checked = false;
    });
}

function loadReviewerName() {
    try {
        const savedName = window.localStorage.getItem(REVIEWER_NAME_KEY);
        if (savedName) {
            reviewerNameInput.value = savedName;
        }
    } catch (error) {
        // Ignore local storage failures and keep the form usable.
    }
}

function saveReviewerName(name) {
    try {
        window.localStorage.setItem(REVIEWER_NAME_KEY, name);
    } catch (error) {
        // Ignore local storage failures and keep the form usable.
    }
}

function showReviewPopup() {
    reviewPopup.classList.remove('hidden');
    reviewPopup.setAttribute('aria-hidden', 'false');
    updateButtonState();
}

function hideReviewPopup() {
    reviewPopup.classList.add('hidden');
    reviewPopup.setAttribute('aria-hidden', 'true');
    updateButtonState();
}

function maybeShowFirstReviewPopup() {
    if (hasShownFirstReviewPopup || hasResolvedFirstReview || !latestReviewContext) {
        return;
    }

    hasShownFirstReviewPopup = true;
    resetReviewForm();
    setReviewStatus('Share feedback on the first answer or skip it.');
    showReviewPopup();
}

function normalizeReviewPayload(reviewAction) {
    const reviewerName = reviewAction === 'skipped'
        ? 'none'
        : (reviewerNameInput.value.trim() || 'none');
    const selectedOptions = reviewTagInputs
        .filter((input) => input.checked)
        .map((input) => input.value);
    const trimmedFeedback = reviewFeedbackInput.value.trim();

    return {
        reviewer_name: reviewerName,
        rating: reviewAction === 'skipped' ? null : (selectedRating || null),
        selected_options: reviewAction === 'skipped' ? [] : selectedOptions,
        feedback: reviewAction === 'skipped' ? 'none' : (trimmedFeedback || 'none'),
        doc_id: latestReviewContext?.docId || 'none',
        query: latestReviewContext?.query || 'none',
        answer: latestReviewContext?.answer || 'none',
        review_action: reviewAction
    };
}

async function uploadPdf() {
    const file = pdfFileInput.files[0];

    if (!file) {
        setStatus('Please choose a PDF file before uploading.', true);
        return;
    }

    isUploading = true;
    updateButtonState();
    setStatus(`Uploading ${file.name}...`);

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            headers: createRequestHeaders(),
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Upload failed.');
        }

        const data = await response.json();
        docIdInput.value = data.doc_id || '';
        setStatus(`PDF indexed successfully. Current document: ${docIdInput.value}`);
        appendMessage(`PDF uploaded. Using document ID: ${docIdInput.value}`, 'bot');
    } catch (error) {
        setStatus(error.message || 'Upload failed.', true);
    } finally {
        isUploading = false;
        updateButtonState();
    }
}

async function sendMessage() {
    const text = userInput.value.trim();
    const docId = docIdInput.value.trim();

    if (!text || isSending) {
        return;
    }

    if (!docId) {
        setStatus('Upload a PDF or enter a document ID before chatting.', true);
        return;
    }

    appendMessage(text, 'user');
    userInput.value = '';

    isSending = true;
    updateButtonState();
    setStatus(`Asking questions about "${docId}"...`);

    const botMessage = appendMessage('Thinking...', 'bot');

    try {
        const formData = new FormData();
        formData.append('query', text);
        formData.append('doc_id', docId);

        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: createRequestHeaders(),
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Chat request failed.');
        }

        if (!response.body) {
            const directResponse = await response.text();
            botMessage.textContent = directResponse;
            if (!hasShownFirstReviewPopup && !hasResolvedFirstReview) {
                latestReviewContext = {
                    query: text,
                    answer: directResponse,
                    docId
                };
                maybeShowFirstReviewPopup();
            }
            setStatus(`Connected to document: ${docId}`);
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        botMessage.textContent = '';

        while (true) {
            const { value, done } = await reader.read();

            if (done) {
                break;
            }

            fullText += decoder.decode(value, { stream: true });
            botMessage.textContent = fullText;
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        fullText += decoder.decode();
        const finalAnswer = fullText.trim() ? fullText : 'No response generated.';
        botMessage.textContent = finalAnswer;
        if (!hasShownFirstReviewPopup && !hasResolvedFirstReview) {
            latestReviewContext = {
                query: text,
                answer: finalAnswer,
                docId
            };
            maybeShowFirstReviewPopup();
        }
        setStatus(`Connected to document: ${docId}`);
    } catch (error) {
        botMessage.textContent = 'Sorry, I could not reach the chat service.';
        setStatus(error.message || 'Chat request failed.', true);
    } finally {
        isSending = false;
        updateButtonState();
        userInput.focus();
    }
}

async function sendReview(reviewAction) {
    if (!latestReviewContext) {
        setReviewStatus('The first answer is not available for review.', true);
        return;
    }

    const payload = normalizeReviewPayload(reviewAction);

    isReviewSubmitting = true;
    updateButtonState();
    setReviewStatus(reviewAction === 'skipped' ? 'Saving skip choice...' : 'Saving review...');

    try {
        if (payload.reviewer_name !== 'none') {
            saveReviewerName(payload.reviewer_name);
        }

        const response = await fetch(`${API_BASE_URL}/review`, {
            method: 'POST',
            headers: createRequestHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Review could not be saved.');
        }

        hasResolvedFirstReview = true;
        resetReviewForm();
        hideReviewPopup();
        setStatus(reviewAction === 'skipped' ? 'Review skipped and stored.' : 'Review saved successfully.');
    } catch (error) {
        setReviewStatus(error.message || 'Review could not be saved.', true);
    } finally {
        isReviewSubmitting = false;
        updateButtonState();
    }
}

uploadBtn.addEventListener('click', uploadPdf);
sendBtn.addEventListener('click', sendMessage);
submitReviewBtn.addEventListener('click', () => sendReview('submitted'));
skipReviewBtn.addEventListener('click', () => sendReview('skipped'));

ratingButtons.forEach((button) => {
    button.addEventListener('click', () => {
        setSelectedRating(Number(button.dataset.rating));
        setReviewStatus('Rating updated.');
    });
});

loadReviewerName();
updateButtonState();

userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

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
const reviewerNameInput = document.getElementById('reviewer-name');
const reviewFeedbackInput = document.getElementById('review-feedback');
const submitReviewBtn = document.getElementById('submit-review-btn');
const reviewStatus = document.getElementById('review-status');
const ratingButtons = Array.from(document.querySelectorAll('.rating-btn'));
const reviewTagInputs = Array.from(document.querySelectorAll('.review-tags input[type="checkbox"]'));

const REVIEWER_NAME_KEY = 'metamorph-reviewer-name';

let isSending = false;
let isUploading = false;
let isReviewSubmitting = false;
let selectedRating = 0;
let latestReviewContext = null;

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
    submitReviewBtn.disabled = isReviewSubmitting || !latestReviewContext;
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

    latestReviewContext = null;
    resetReviewForm();

    isSending = true;
    updateButtonState();
    setStatus(`Asking questions about "${docId}"...`);
    setReviewStatus('Waiting for the latest answer before saving a review.');

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
            latestReviewContext = {
                query: text,
                answer: directResponse,
                docId
            };
            resetReviewForm();
            setReviewStatus('Answer ready. Add a rating or notes if you want.');
            updateButtonState();
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
        latestReviewContext = {
            query: text,
            answer: finalAnswer,
            docId
        };
        resetReviewForm();
        setReviewStatus('Answer ready. Add a rating or notes if you want.');
        updateButtonState();
        setStatus(`Connected to document: ${docId}`);
    } catch (error) {
        botMessage.textContent = 'Sorry, I could not reach the chat service.';
        latestReviewContext = null;
        setReviewStatus('No answer was captured for review yet.', true);
        updateButtonState();
        setStatus(error.message || 'Chat request failed.', true);
    } finally {
        isSending = false;
        updateButtonState();
        userInput.focus();
    }
}

async function submitReview() {
    if (!latestReviewContext) {
        setReviewStatus('Ask a question and wait for an answer before reviewing.', true);
        return;
    }

    const reviewerName = reviewerNameInput.value.trim();
    if (!reviewerName) {
        setReviewStatus('Please enter the reviewer name before saving.', true);
        reviewerNameInput.focus();
        return;
    }

    if (!selectedRating) {
        setReviewStatus('Choose a rating from 1 to 5 before saving.', true);
        return;
    }

    const selectedOptions = reviewTagInputs
        .filter((input) => input.checked)
        .map((input) => input.value);

    const payload = {
        reviewer_name: reviewerName,
        rating: selectedRating,
        selected_options: selectedOptions,
        feedback: reviewFeedbackInput.value.trim(),
        doc_id: latestReviewContext.docId,
        query: latestReviewContext.query,
        answer: latestReviewContext.answer
    };

    isReviewSubmitting = true;
    updateButtonState();
    setReviewStatus('Saving review...');

    try {
        saveReviewerName(reviewerName);

        const response = await fetch(`${API_BASE_URL}/review`, {
            method: 'POST',
            headers: createRequestHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Review could not be saved.');
        }

        resetReviewForm();
        setReviewStatus(`Review saved for ${reviewerName}.`);
    } catch (error) {
        setReviewStatus(error.message || 'Review could not be saved.', true);
    } finally {
        isReviewSubmitting = false;
        updateButtonState();
    }
}

uploadBtn.addEventListener('click', uploadPdf);
sendBtn.addEventListener('click', sendMessage);
submitReviewBtn.addEventListener('click', submitReview);

ratingButtons.forEach((button) => {
    button.addEventListener('click', () => {
        setSelectedRating(Number(button.dataset.rating));
        setReviewStatus('Review details updated.');
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

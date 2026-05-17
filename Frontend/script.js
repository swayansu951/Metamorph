const API_BASE_URL = window.location.protocol === 'file:'
    ? 'http://127.0.0.1:8000'
    : window.location.origin;
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
const newSessionBtn = document.getElementById('new-session-btn');
const sessionList = document.getElementById('session-list');
const reviewPopup = document.getElementById('review-popup');
const reviewerNameInput = document.getElementById('reviewer-name');
const reviewFeedbackInput = document.getElementById('review-feedback');
const submitReviewBtn = document.getElementById('submit-review-btn');
const skipReviewBtn = document.getElementById('skip-review-btn');
const reviewStatus = document.getElementById('review-status');
const ratingButtons = Array.from(document.querySelectorAll('.rating-btn'));
const reviewTagInputs = Array.from(document.querySelectorAll('.review-tags input[type="checkbox"]'));

const REVIEWER_NAME_KEY = 'metamorph-reviewer-name';
const SESSIONS_KEY = 'metamorph-chat-sessions';
const ACTIVE_SESSION_KEY = 'metamorph-active-session';

let isSending = false;
let isUploading = false;
let isReviewSubmitting = false;
let sessions = [];
let activeSessionId = '';
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

function createSession(title = 'New chat') {
    const id = `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return {
        id,
        title,
        docId: '',
        docName: '',
        summary: 'No conversation yet.',
        messages: [],
        updatedAt: new Date().toISOString()
    };
}

function saveSessions() {
    try {
        window.localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
        window.localStorage.setItem(ACTIVE_SESSION_KEY, activeSessionId);
    } catch (error) {
        // Keep chat usable if local storage is blocked.
    }
}

function getActiveSession() {
    return sessions.find((session) => session.id === activeSessionId) || null;
}

function summarizeSession(session) {
    const lastUser = [...session.messages].reverse().find((message) => message.sender === 'user');
    const lastBot = [...session.messages].reverse().find((message) => message.sender === 'bot');
    if (!lastUser && !lastBot) {
        return 'No conversation yet.';
    }
    const userPart = lastUser ? `Q: ${lastUser.text}` : '';
    const botPart = lastBot ? `A: ${lastBot.text}` : '';
    return `${userPart} ${botPart}`.trim().slice(0, 170);
}

function formatSessionTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return 'Just now';
    }

    return date.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function renderSessions() {
    sessionList.innerHTML = '';

    if (!sessions.length) {
        const emptyState = document.createElement('div');
        emptyState.className = 'session-empty';
        emptyState.textContent = 'No sessions yet.';
        sessionList.appendChild(emptyState);
        return;
    }

    sessions
        .slice()
        .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
        .forEach((session) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `session-card${session.id === activeSessionId ? ' active' : ''}`;
            button.dataset.sessionId = session.id;

            const topLine = document.createElement('div');
            topLine.className = 'session-card-topline';

            const title = document.createElement('div');
            title.className = 'session-card-title';
            title.textContent = session.title || 'New chat';

            const state = document.createElement('span');
            state.className = 'session-card-state';
            state.textContent = session.id === activeSessionId ? 'Active' : 'Continue';

            topLine.append(title, state);

            const doc = document.createElement('div');
            doc.className = 'session-card-doc';
            const documentLabel = session.docName || session.docId;
            doc.innerHTML = `<span>Document</span>${documentLabel ? documentLabel : 'Web only'}`;

            const summary = document.createElement('div');
            summary.className = 'session-card-summary';
            summary.innerHTML = `<span>Memory</span>${session.summary || 'No conversation yet.'}`;

            const updated = document.createElement('div');
            updated.className = 'session-card-updated';
            updated.textContent = `Updated ${formatSessionTime(session.updatedAt)}`;

            button.append(topLine, doc, summary, updated);
            button.addEventListener('click', () => selectSession(session.id));
            sessionList.appendChild(button);
        });
}

function restoreChat(session) {
    chatBox.innerHTML = '';
    if (!session.messages.length) {
        appendMessage('Hello! Upload a PDF to work from a document, or ask directly for web-backed help.', 'bot');
        return;
    }
    session.messages.forEach((message) => appendMessage(message.text, message.sender));
}

function selectSession(sessionId) {
    const session = sessions.find((item) => item.id === sessionId);
    if (!session) {
        return;
    }
    activeSessionId = session.id;
    docIdInput.value = session.docId || '';
    restoreChat(session);
    setStatus(session.docId ? `Continuing with document: ${session.docId}` : 'Continuing a web-backed session.');
    saveSessions();
    renderSessions();
}

function startNewSession() {
    const session = createSession();
    sessions.unshift(session);
    activeSessionId = session.id;
    docIdInput.value = '';
    latestReviewContext = null;
    restoreChat(session);
    setStatus('New chat started. Upload a PDF or ask a web-backed question.');
    saveSessions();
    renderSessions();
    userInput.focus();
}

function updateActiveSession(updater) {
    const session = getActiveSession();
    if (!session) {
        return;
    }
    updater(session);
    session.summary = summarizeSession(session);
    session.updatedAt = new Date().toISOString();
    saveSessions();
    renderSessions();
}

function loadSessions() {
    try {
        const stored = JSON.parse(window.localStorage.getItem(SESSIONS_KEY) || '[]');
        sessions = Array.isArray(stored) ? stored : [];
        activeSessionId = window.localStorage.getItem(ACTIVE_SESSION_KEY) || '';
    } catch (error) {
        sessions = [];
        activeSessionId = '';
    }

    if (!sessions.length) {
        startNewSession();
        return;
    }

    if (!sessions.some((session) => session.id === activeSessionId)) {
        activeSessionId = sessions[0].id;
    }

    selectSession(activeSessionId);
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
        updateActiveSession((session) => {
            session.docId = docIdInput.value;
            session.docName = file.name;
            session.title = file.name.replace(/\.pdf$/i, '') || 'Document chat';
            session.messages.push({
                sender: 'bot',
                text: `PDF uploaded. Using document ID: ${docIdInput.value}`
            });
        });
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

    appendMessage(text, 'user');
    userInput.value = '';

    isSending = true;
    updateButtonState();
    setStatus(docId ? `Asking questions about "${docId}"...` : 'Asking with web fallback...');

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
        updateActiveSession((session) => {
            session.docId = docId;
            if (!docId) {
                session.docName = '';
            }
            session.title = session.title === 'New chat' ? text.slice(0, 48) || 'New chat' : session.title;
            session.messages.push({ sender: 'user', text });
            session.messages.push({ sender: 'bot', text: directResponse });
            });
            setStatus(docId ? `Connected to document: ${docId}` : 'Answered with web fallback.');
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
        updateActiveSession((session) => {
            session.docId = docId;
            if (!docId) {
                session.docName = '';
            }
            session.title = session.title === 'New chat' ? text.slice(0, 48) || 'New chat' : session.title;
            session.messages.push({ sender: 'user', text });
            session.messages.push({ sender: 'bot', text: finalAnswer });
        });
        if (!hasShownFirstReviewPopup && !hasResolvedFirstReview) {
            latestReviewContext = {
                query: text,
                answer: finalAnswer,
                docId
            };
            maybeShowFirstReviewPopup();
        }
        setStatus(docId ? `Connected to document: ${docId}` : 'Answered with web fallback.');
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
newSessionBtn.addEventListener('click', startNewSession);
submitReviewBtn.addEventListener('click', () => sendReview('submitted'));
skipReviewBtn.addEventListener('click', () => sendReview('skipped'));

ratingButtons.forEach((button) => {
    button.addEventListener('click', () => {
        setSelectedRating(Number(button.dataset.rating));
        setReviewStatus('Rating updated.');
    });
});

loadReviewerName();
loadSessions();
updateButtonState();

userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

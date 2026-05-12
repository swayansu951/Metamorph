const API_BASE_URL = window.location.origin === 'null' ? 'http://127.0.0.1:8000' : window.location.origin;

const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const uploadBtn = document.getElementById('upload-btn');
const pdfFileInput = document.getElementById('pdf-file');
const docIdInput = document.getElementById('doc-id');
const statusText = document.getElementById('status-text');

let isSending = false;
let isUploading = false;

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
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Chat request failed.');
        }

        if (!response.body) {
            botMessage.textContent = await response.text();
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
        botMessage.textContent = fullText.trim() ? fullText : 'No response generated.';
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

uploadBtn.addEventListener('click', uploadPdf);
sendBtn.addEventListener('click', sendMessage);

userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

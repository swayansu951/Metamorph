# Metamorph: Local Research Assistant

Metamorph is a local-first research assistant that combines document-based RAG, web retrieval, and agent orchestration. It lets a user upload a PDF, ask questions about that document, or fall back to web search when the question needs fresh external information.

The project was built to explore practical RAG system design with LangGraph, LangChain, semantic chunking, FAISS vector search, BM25 retrieval, web scraping, session memory, and a simple FastAPI frontend.

## Key Learning Areas

- Agent orchestration with LangGraph and LangChain
- PDF ingestion and retrieval-augmented generation
- Semantic chunking and embedding-based retrieval
- FAISS vector indexing for local document search
- Hybrid retrieval using semantic search and BM25-style keyword search
- Web search and scraping with DDGS and BeautifulSoup
- Session memory, review capture, and streaming responses

## Features

- Upload and index PDF documents.
- Ask document-grounded questions through a chat interface.
- Automatically route questions between document RAG, web search, and direct LLM response.
- Use semantic chunking to preserve meaning across retrieved context.
- Store document chunks and metadata locally in `rag_db`.
- Retrieve fresh web context with DDGS search and BeautifulSoup scraping.
- Store web text, image, and video payloads in `search_db`.
- Stream answers from the backend to the frontend.
- Keep lightweight session memory for continuing previous chats.
- Collect first-answer feedback through a review popup.

## Architecture Overview

```text
Frontend chat UI
        |
        v
FastAPI backend
        |
        v
LangGraph query router -------|
   |            |             |
   v            v             v
PDF RAG     Web RAG       Direct LLM
   |            |
   v            v
FAISS DB     DDGS + BS4 + SearchDB
```

## How It Works

### 1. PDF RAG pipeline

When a PDF is uploaded, the backend stores it in `uploads` and indexes it with the simple RAG pipeline.

- `PyMuPDF` extracts text from the PDF.
- Sentence embeddings are generated with `all-mpnet-base-v2`.
- A semantic chunker groups related sentences and avoids splitting meaningful context too aggressively.
- Chunk embeddings are stored in a FAISS HNSW index.
- Chunk metadata is saved beside the FAISS index under `rag_db/documents/<doc_id>`.

At question time, the retriever embeds the query, searches the FAISS index, builds a context window, and sends the most relevant context to the LLM.

### 2. Query routing and orchestration

The main router in `query_router.py` uses LangGraph to decide whether a user query should go to:

- `RAG_SEARCH` when a selected document should answer the question.
- `WEB_SEARCH` when the query asks for current, recent, or external information.
- `LLM_RESPONSE` for greetings or simple direct conversation.

The graph also checks whether the current context window is enough to answer the question. If not, it slides to the next window before generating the final response.

### 3. Web retrieval pipeline

The web pipeline combines query filtering, search, scraping, storage, and response generation.

- A query filter classifies the user request into domain, freshness, media need, and search depth.
- DDGS retrieves text, news, image, or video results.
- BeautifulSoup extracts page text, headings, links, tables, images, and videos.
- SearchDB stores payloads and vectors for text, image, and video content.
- The web LLM generates a final response from the retrieved web context.

The web pipeline also tracks agent activity using UUID-based agent registration.

### 4. Frontend and API

The FastAPI app serves the frontend and exposes endpoints for:

- `POST /upload` - upload and index a PDF
- `POST /chat` - ask a question and stream the answer
- `POST /review` - save first-answer review feedback
- `GET /session-memory/{session_id}` - load saved session memory
- `POST /session-memory` - save session memory
- `DELETE /session-memory/{session_id}` - delete session memory

The frontend supports PDF upload, chat, session switching, local session storage, answer streaming, and review collection.

## Project Structure

```text
.
|-- app.py                  # FastAPI backend and API endpoints
|-- query_router.py         # LangGraph routing and answer workflow
|-- run_server.py           # Uvicorn server entry point
|-- Frontend/               # HTML, CSS, and JavaScript chat UI
|-- simple_rag/             # PDF ingestion, chunking, FAISS indexing, retrieval
|-- tool/web_scraping/      # DDGS search, BS4 scraper, SearchDB, web LLM pipeline
|-- hybrid_rag/             # Experimental hybrid RAG implementation
|-- rag_db/                 # Local indexed document database
|-- search_db/              # Local web retrieval database
|-- memory/                 # Session memory files
|-- reviews/                # Stored review feedback
`-- uploads/                # Uploaded PDFs
```

## Setup

1. Create and activate a Python environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

Some modules used by the web and orchestration pipeline may also require packages such as `langchain-ollama`, `python-dotenv`, `huggingface_hub`, `beautifulsoup4`, `lxml`, `requests`, `ddgs`, and `rank-bm25` if they are not already installed.

3. Add a Hugging Face token if needed.

Create a `.env` file:

```env
HF_TOKEN=your_huggingface_token_here
```

4. Make sure Ollama is running and the configured models are available.

The project currently uses local Ollama models such as:

```text
gemma4-e4b_q4_k_m
llama3.2:3b
```
You can choose your own local model and connect through Ollama

## Run the App

Start the backend:

```bash
python run_server.py
```
```bash
ngrok http 8000
```
The server runs on:

```text
http://localhost:8000
```

Open the app in a browser at the same address.

Note: `Frontend/script.js` currently points to an ngrok URL through `API_BASE_URL`. For local testing, change it to:

```js
const API_BASE_URL = "http://localhost:8000";
```

## Challenges Faced

- Router failures during orchestration, especially when graph edges were not connected in the correct sequence.
- Context overflow when too much retrieved data was passed into the model at once.
- Maintaining answer quality while using sliding context windows.
- Building a web retrieval flow that could handle text, image, and video metadata.
- Debugging streamed text that was accidentally printed in the server console instead of being passed cleanly to the web app.

## Future Improvements

- Add stronger source citation support in final answers.
- Improve dependency tracking in `requirements.txt`.
- Add automated tests for PDF ingestion, routing, and web search fallback.
- Add better error messages when Ollama models or local indexes are missing.
- Add a production-ready frontend API configuration instead of hardcoding the backend URL.

## Contribution

If you like to introduce some changes or want to be a part of this project you are wellcomed to contribute in this project: ping me on @sahuswayansu240@gmail.com
## License

This project is licensed under the MIT License. See `LICENSE` for details.

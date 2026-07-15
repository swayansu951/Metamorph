from pathlib import Path
import pickle
import re

import faiss
import numpy as np
from rank_bm25 import BM25Plus

from database.embedding_model import model
from database.pdf_loader import load_pdf
from database.semantic_chunker import semantic_chunker
from database.summarizer import summarize_document, summarize_chunks

dim = model.get_sentence_embedding_dimension()

def tokenize(text):
    """tokenize the texts"""

    return re.findall(r"\b\w+\b", text.lower())


def create_summary_index(dim):
    """summaries the document for easy retrieval of responce"""

    index_path = Path("rag_db/documents") / "summary_index.faiss"

    if index_path.exists():
        print("Loading existing summary index...")
        index = faiss.read_index(str(index_path))
    else:
        print("Creating new summary index...")
        index = faiss.IndexFlatL2(dim)

    return index


def ingest_pdf(file_path, doc_id=None):
    """Add every thing to a folder storing the summaries, the tokens, the chunks. 
    file_path is default rag_db, and the doc_id is none, cause to be added according to the pdf's name"""

    file_path = str(file_path)
    doc_id = doc_id or Path(file_path).stem

    rag_db_path = Path("rag_db")
    documents_path = rag_db_path / "documents"
    rag_db_path.mkdir(exist_ok=True)
    documents_path.mkdir(parents=True, exist_ok=True)

    text = load_pdf(file_path)
    sentence = text.split(". ")
    text_embedding = model.encode(sentence).astype("float32")

    doc_summary = summarize_document(text)
    doc_embedding = model.encode([doc_summary]).astype("float32")

    summary_index = create_summary_index(dim)
    summary_index.add(doc_embedding)
    faiss.write_index(summary_index, str(documents_path / "summary_index.faiss"))

    doc_folder = documents_path / doc_id
    doc_folder.mkdir(parents=True, exist_ok=True)

    chunks = semantic_chunker(sentence, text_embedding)
    chunk_summaries = summarize_chunks(chunks)
    chunk_summary_embeddings = model.encode(chunk_summaries).astype("float32")
    chunk_embeddings = model.encode(chunks).astype("float32")

    chunk_summary_index = faiss.IndexHNSWFlat(dim, 32)
    chunk_index = faiss.IndexHNSWFlat(dim, 32)

    chunk_summary_index.add(chunk_summary_embeddings)
    chunk_index.add(chunk_embeddings)

    faiss.write_index(chunk_summary_index, str(doc_folder / "chunk_summary_index.faiss"))
    faiss.write_index(chunk_index, str(doc_folder / "chunk_index.faiss"))

    tokenized_chunks = [tokenize(chunk) for chunk in chunks]
    bm25 = BM25Plus(tokenized_chunks)
    with (doc_folder / "bm25.pkl").open("wb") as bm25_file:
        pickle.dump(bm25, bm25_file)

    metadata = {}

    summary_metadata = {
        "doc_id": doc_id,
        "summary": doc_summary,
    }
    summary_metadata_path = rag_db_path / "summary_metadata.pkl"

    if summary_metadata_path.exists():
        with summary_metadata_path.open("rb") as summary_metadata_file:
            existing = pickle.load(summary_metadata_file)
    else:
        existing = []

    existing.append(summary_metadata)

    with summary_metadata_path.open("wb") as summary_metadata_file:
        pickle.dump(existing, summary_metadata_file)

    for i, chunk in enumerate(chunks):
        metadata[i] = {
            "chunk_id": i,
            "chunk_text": chunk,
            "chunk_summary": chunk_summaries[i],
            "embedding": chunk_embeddings[i],
        }

    with (doc_folder / "metadata.pkl").open("wb") as metadata_file:
        pickle.dump(metadata, metadata_file)

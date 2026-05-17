from pathlib import Path
import pickle
import re
import faiss
import numpy as np
from simple_rag.database.embedder import embed_model
from simple_rag.database.load_pdf import extract_load_pdf
from simple_rag.database.semantic_chunker import semantic_chunker

def tokenize(text):
    """tokenize the texts"""

    return re.findall(r"\b\w+\b", text.lower())

def ingest_pdf(file_path, doc_id=None):
    """Add every thing to a folder storing the summaries, the tokens, the chunks. 
    file_path is default rag_db, and the doc_id is none, cause to be added according to the pdf's name"""

    file_path = str(file_path)
    doc_id = doc_id or Path(file_path).stem

    rag_db_path = Path("rag_db")
    documents_path = rag_db_path / "documents"
    rag_db_path.mkdir(exist_ok=True)
    documents_path.mkdir(parents=True, exist_ok=True)

    text = extract_load_pdf(file_path)
    sentence = text.split(". ")
    text_embedding = embed_model.encode(sentence).astype("float32")
    dim = embed_model.get_sentence_embedding_dimension()

    doc_folder = documents_path / doc_id
    doc_folder.mkdir(parents=True, exist_ok=True)

    chunks = semantic_chunker(sentence, text_embedding)
    chunk_embeddings = embed_model.encode(chunks).astype("float32")
    chunk_index = faiss.IndexHNSWFlat(dim, 32)
    chunk_index.add(chunk_embeddings)

    faiss.write_index(chunk_index, str(doc_folder / "chunk_index.faiss"))

    tokenized_chunks = [tokenize(chunk) for chunk in chunks]

    metadata = {}
    
    for i, chunk in enumerate(chunks):
        metadata[i] = {
            "chunk_id": i,
            "chunk_text": chunk,
            "embedding": chunk_embeddings[i],
        }

    with (doc_folder / "metadata.pkl").open("wb") as metadata_file:
        pickle.dump(metadata, metadata_file)

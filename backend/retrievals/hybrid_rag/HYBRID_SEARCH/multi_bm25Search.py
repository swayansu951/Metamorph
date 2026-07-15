import os
import pickle
import re

def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower())


def bm25_search_all(query, top_k=5):
    tokenized_query = tokenize(query)
    results = []
    base_path = "rag_db/documents"

    if not os.path.isdir(base_path):
        return []

    for doc_id in os.listdir(base_path):
        doc_path = os.path.join(base_path, doc_id)

        try:
            metadatas = {}
            for doc_id in os.listdir(base_path):
                    doc_path = os.path.join(base_path, doc_id, "metadata.pkl")
                    if os.path.isfile(doc_path):
                        with open(doc_path, 'rb') as f:
                                metadatas[doc_id] = pickle.load(f)
            
            bm25 = {}
            for doc_id in os.listdir(base_path):
                    doc_path = os.path.join(base_path, doc_id, "bm25.pkl")
                    if os.path.isfile(doc_path):
                        with open(doc_path, 'rb') as f:
                                bm25[doc_id] = pickle.load(f)

            # bm25 = pickle.load(open(f"{doc_path}/bm25.pkl", "rb"))
            # metadata = pickle.load(open(f"{doc_path}/metadata.pkl", "rb"))

            scores = bm25.get_scores(tokenized_query)

            for i, score in enumerate(scores):
                chunk = metadatas.get(i, {})
                results.append({
                    "doc_id": doc_id,
                    "chunk_id": i,
                    "score": float(score),
                    "chunk_text": chunk.get("chunk_text", ""),
                    "chunk_summary": chunk.get("chunk_summary", ""),
                })

        except:
            continue

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return results[:top_k]
# under progress
import pickle
import re


def tokenize(text):
    """Tokenize the text for the bm25 searching algorithm"""

    return re.findall(r"\b\w+\b", text.lower())

def bm25_search(query, doc_id, top_k=5):
    """bm25 : best match 25 algorithm, 
    This helps to retrieve more relevant and accurate keyword based context retrieval"""

    bm25 = pickle.load(open(f"rag_db/documents/{doc_id}/bm25.pkl", "rb"))
    metadata = pickle.load(open(f"rag_db/documents/{doc_id}/metadata.pkl", "rb"))
    
    tokenized_query = tokenize(query)
    scores = bm25.get_scores(tokenized_query)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    
    results = []
    for i in top_indices:
        results.append({
            "chunk_id": i,
            "score": float(scores[i])
        })
    
    return results


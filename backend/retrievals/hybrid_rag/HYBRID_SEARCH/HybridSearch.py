from backend.retrievals.hybrid_rag.HybridRetriever.ChunkRetriever import ChunkRetriever
from backend.retrievals.hybrid_rag.HYBRID_SEARCH.bm25_search import bm25_search

def hybrid_search(query, doc_id, top_k=5, k =60):
    """Hybrid searching algorithm for efficient searching for the most relevent context according to the query,
    by usign bm25 search and hybrid-chunk retriever"""

    vector_retriever = ChunkRetriever(doc_id)

    vector_result = vector_retriever.retrieve_chunks(query, doc_id)
    bm25_result = bm25_search(query, doc_id)

    scores = {}

    for rank, r in enumerate(vector_result):
        chunk = r['chunk_text']
        scores[chunk] = scores.get(chunk, 0) + 1 / (k + rank+ 1)

    for rank, r in enumerate(bm25_result):
        chunk = r['chunk_text']
        scores[chunk] = scores.get(chunk, 0) + 1 / (k + rank + 1)

    sorted_chunk = sorted(scores.items(), key = lambda x: x[1], reverse=True)

    return [chunk for chunk in sorted_chunk[:top_k]]

from backend.retrievals.hybrid_rag.HYBRID_SEARCH.multi_bm25Search import bm25_search_all


def hybrid_search_all(query, top_k=5):
    return bm25_search_all(query, top_k=top_k)
# under progress
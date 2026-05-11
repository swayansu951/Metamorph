import faiss
import pickle
from retriever.query_embedder import embed_query

summary_index = faiss.read_index("rag_db/documents/summary_index.faiss")  

def find_documents(query, top_k=5):
    query_embedding = embed_query(query)
    distances, ids = summary_index.search(query_embedding, top_k)
    return ids[0]

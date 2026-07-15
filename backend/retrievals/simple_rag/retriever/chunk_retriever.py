import faiss
import pickle
from backend.retrievals.simple_rag.retriever.query_embedder import embed_query

class Chunk_retriever:
    def __init__(self, doc_id):
        self.doc_id = doc_id
        with open(f"rag_db/documents/{doc_id}/metadata.pkl", "rb") as metadata_file:
            self.metadata = pickle.load(metadata_file)
        
    
    def retrieve_chunks(self, query, top_k=5):

        query_embedding = embed_query(query)
        chunk_index = faiss.read_index(f"rag_db/documents/{self.doc_id}/chunk_index.faiss")
        chunk_distances, chunk_ids = chunk_index.search(query_embedding, top_k)
        
        results = []

        for idx, chunk_id in enumerate(chunk_ids[0]):

            if chunk_id in self.metadata:

                results.append({
                    "chunk_text": self.metadata[chunk_id]["chunk_text"],
                    "chunk_distance": float(chunk_distances[0][idx])
                })

        return results

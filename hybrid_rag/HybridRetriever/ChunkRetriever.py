import faiss
import pickle
from query_embedding import embed_query

class ChunkRetriever:
    def __init__(self, doc_id):
        self.doc_id = doc_id
        self.index = faiss.read_index(f"rag_db/documents/{doc_id}/chunk_summary_index.faiss")
        self.metadata = pickle.load(open(f"rag_db/documents/{doc_id}/metadata.pkl", "rb"))
        self.chunk_index = faiss.read_index(f"rag_db/documents/{self.doc_id}/chunk_index.faiss")

    def retrieve_chunks(self,query, top_k=5):
        """Retrieve chunks from the top 5(can be changed) most relevent chunks,
            on the basis of ranks of each chunk,
            to feed LLM for generating responce"""

        query_embedding = embed_query(query).astype("float32")

        summary_distances, summary_ids = self.index.search(query_embedding, top_k)
        chunk_distances, chunk_ids = self.chunk_index.search(query_embedding, top_k)
        
        results = []

        for rank, chunk_id in enumerate(summary_ids[0]):
            
            if chunk_id == -1:
                continue
            results[chunk_id] = {
                "chunk_id" : int(chunk_id),
                "score" : float(summary_distances[0][rank]),
                "source" : "summary"
            }
            chunk_data = self.metadata[chunk_id]

        for rank , chunk_id in enumerate(chunk_ids[0]):
            if chunk_id == -1:
                continue
            if chunk_id in results:
                results[chunk_id]["score"] += float(chunk_distances[0][rank])
            else : 
                results[chunk_id] = {
                    "chunk_id" : int(chunk_id),
                    "score" : float(chunk_distances[0][rank]),
                    "source" : "chunk"
                }
            # results.append({
            #     "chunk_id":chunk_id,
            #     "chunk_text": chunk_data["chunk_text"],
            #     "chunk_summary": chunk_data["chunk_summary"],
            #     "summary_distance": summary_distances[0][rank]
            # })

        return list(results.values())
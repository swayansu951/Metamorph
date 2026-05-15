import faiss
import pickle
from query_embedding import embed_query
import os

# for future updates
class MultiChunkRetriever:
    def __init__(self):
        self.path = "rag_db/documents"
        base_path = "rag_db/documents"
        metadatas = {}
        chunk_summary = {}
        chunk_index = {}

        for doc_id in os.listdir(base_path):
            doc_path = os.path.join(base_path, doc_id, "chunk_index.faiss")
            if os.path.isfile(doc_path):
                chunk_summary[doc_id] = faiss.read_index(f)

        self.chunk_index = chunk_index  

        for doc_id in os.listdir(base_path):
            doc_path = os.path.join(base_path, doc_id, "chunk_summary_index.faiss")
            if os.path.isfile(doc_path):
                chunk_summary[doc_id] = faiss.read_index(f)        
        
        self.summary_index = chunk_summary

        for doc_id in os.listdir(base_path):
            doc_path = os.path.join(base_path, doc_id, "metadata.pkl")
            if os.path.isfile(doc_path):
                with open(doc_path, 'rb') as f:
                        metadatas[doc_id] = pickle.load(f)
        
        self.metadatas = metadatas
    
    def load_all(self):
        docs = {}
        for doc in os.listdir(self.path):
            doc_path = os.path.join(self.path, doc)

        faiss_index_path = os.path.join(self.path, "summary_index.faiss")
        pkl_path = os.path.join(doc_path, "bm25.pkl")

        if os.path.exists(faiss_index_path) and os.path.exists(pkl_path):
            index = faiss.read_index(faiss_index_path)

            with open(pkl_path, 'rb') as f:
                chunks = pickle.load(f)

            docs[doc] = {
                "index" : self.chunk_index,
                "summary_index" : self.summary_index,
                "chunks" : chunks,
                "metadata" : self.metadatas
            }
        return docs

    def search_all(self, query, top_k=5):
        """To feed all the relevent docs and to find from all the relevent chunks,
          for generating more complex and multi query anwsers"""

        query_embedder = embed_query(query).astype("float32")
        summary_distances, summary_ids = self.summary_index.search(query_embedder, top_k)
        chunk_distances, chunk_ids = self.chunk_index.search(query_embedder, top_k)

        results = []

        for rank, chunk_id in enumerate(summary_ids[0]):
            if chunk_id == -1:
                continue
            results[chunk_id] = {
                "chunk_id" : int(chunk_id),
                "score" : float(summary_distances)[0][rank],
                "source" : "summary"
            }

            chunk_data = self.metadatas[chunk_id]

        for rank, chunk_id in enumerate(chunk_ids[0]):
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

        return list(results.values())
    # under progress
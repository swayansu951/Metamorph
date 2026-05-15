import faiss
import os

dimensions = 384

os.makedirs("rag_db/documents", exist_ok=True)
summary_index = faiss.IndexHNSWFlat(dimensions, 32)

summary_index.hnsw.efConstruction = 200
summary_index.hnsw.efSearch = 64

faiss.write_index(summary_index, "rag_db/documents/summary_index.faiss")
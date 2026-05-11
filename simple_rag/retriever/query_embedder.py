from sentence_transformers import SentenceTransformer
from database.embedder import model
model = model

def embed_query(query):
    return model.encode([query]).astype('float32')

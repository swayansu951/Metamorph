from sentence_transformers import SentenceTransformer
from database.embedding_model import model
model = model

def embed_query(query):
    """To embed multi-query inputs and generate relevent responce"""
    
    return model.encode([query]).astype('float32')
# under progress
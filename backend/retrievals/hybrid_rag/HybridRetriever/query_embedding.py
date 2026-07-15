from backend.retrievals.hybrid_rag.database.embedding_model import model

def embed_query(query):
    """To embed multi-query inputs and generate relevent responce"""
    
    return model.encode([query]).astype('float32')
# under progress
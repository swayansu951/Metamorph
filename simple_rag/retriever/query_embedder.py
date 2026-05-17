from simple_rag.database.embedder import embed_model as model

def embed_query(query):
    return model.encode([query]).astype('float32')

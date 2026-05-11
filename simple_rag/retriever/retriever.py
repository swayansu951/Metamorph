from retriever.document_router import find_documents
from retriever.chunk_retriever import Chunk_retriever

retriever = Chunk_retriever.retrieve_chunks()
def retrieve(query):
    docs = find_documents(query)
    context = []

    for doc in docs:
        doc_id = f"doc_{doc}"
        chunks = retriever(query, doc_id)
        context.extend(chunks)
   
    final_chunks = context
   
    return final_chunks
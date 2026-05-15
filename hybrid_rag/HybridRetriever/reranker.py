from sentence_transformers import CrossEncoder
import torch

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device="cuda") if torch.cuda.is_available() else CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device="cpu")

def rerank(query, chunks):
    """Reranker : to loop the retrieved process until the retrieved responce is not the most accurate one,
        according to the scores this performs reranking"""
    
    pairs = [[query, chunk["chunk_text"]] for chunk in chunks]
    scores = reranker.predict(pairs)

    for i, score in enumerate(scores):
        chunks[i]["rerank_score"] = float(score)

    chunks.sort( key =lambda x: x["rerank_score"], reverse=True)
    
    # return [chunk for chunk, score in chunks[:top_k]]
    return chunks
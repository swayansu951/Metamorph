"""chunks the text using semantically\n
    separates text according to the similarity"""
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np 

def SemanticChunker(text, embedding, soft_limit=350, hard_limit=550, threshold =0.75):
    """ split text intelligently into meaningful, size-controlled segments that preserve semantic relationships, \n
        making embeddings and downstream tasks (like search, summarization, or prediction) much more effective.\n
        - soft_limit : preferred size, tries to split earlier if the similarity drops\n
        - hard_limit : absolute cutoff to avoid oversized chunks\n
        - threshold : To make sure the sentences groped are sematically related, if the similarity is low a new chunk starts\n 
    """
    chunks = []
    current_chunk =[]
    current_token = 0

    for i, sentence in enumerate(text):

        token = len(sentence.split(". "))
        current_chunk.append(sentence)
        current_token += token

        if i > 0 and current_token > soft_limit:
            sim = cosine_similarity([embedding[i]],[embedding[i-1]])[0][0]

            if sim < threshold:
                chunks.append(" ".join(current_chunk))
                current_token = 0
                current_chunk = []

        if current_token > hard_limit:
            chunks.append(" ".join(current_chunk))
            current_chunk =[]
            current_token = 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))
 
    windows = []
    window_size = 2

    for i in range(len(chunks) - window_size + 1):
        window = " ".join(chunks[i:i + window_size])
        windows.append(window)
        
    all_chunks = chunks + windows
    
    return all_chunks


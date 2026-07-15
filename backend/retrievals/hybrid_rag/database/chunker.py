def chunk_text(text, size=500, overlap=100):
    """divide the texts into small chunks to feed in vector DB
    the size is 500 by default (can be changed) and the overlap is 100 to reduce data loss(can be changed)"""
    
    chunks = []
    start = 0

    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap

    return chunks
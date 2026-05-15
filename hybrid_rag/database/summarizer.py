def summarize_document(text):
    """small summarized portion of the document (*this is not a effecient way)"""
    return text[:1000]
    # Placeholder for summarization logic
    # You can use a pre-trained model or an API to generate summaries

def summarize_chunks(chunks):
    """small summarized portion of the chunks to retrieve more accurate chunks afterwards (*this is not a effectient way)"""
    return [chunk[:150] for chunk in chunks]
    # Placeholder for summarization logic for chunks
    # You can use a pre-trained model or an API to generate summaries for each chunk
    
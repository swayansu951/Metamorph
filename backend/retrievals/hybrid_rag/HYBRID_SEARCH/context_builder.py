def build_context(chunks, max_chars=5000):
    """context for preventing bottle-necking the memory"""
    
    context = ""

    for chunk in chunks:
        if isinstance(chunk, dict):
            chunk_text = chunk.get("chunk_text") or chunk.get("chunk_summary") or ""
        else:
            chunk_text = str(chunk)

        if not chunk_text:
            continue

        block = f"\n{chunk_text}\n"

        if len(context) + len(block) > max_chars:
            break
        context += block

    return context

def build_context(chunks, max_chars=4196):
    context = ""

    for chunk in chunks:
        text = chunk.get("chunk_text", str(chunk)) if isinstance(chunk, dict) else str(chunk)
        block = f"\n{text}\n"

        remaining = max_chars - len(context)
        if remaining <= 0:
            print("[-] context overloaded !")
            break

        if len(block) > remaining:
            print("[-] context overloaded ! truncating chunk")
            context += block[:remaining]
            break

        context += block

    return context
def build_context(chunks, max_chars= 4196):
    context= ""

    for chunk in chunks:
        block = f"\n{chunk}\n"

        if len(context) + len(block) > max_chars:
            print("[-] context overloaded !")
            break
        context += block

    return context
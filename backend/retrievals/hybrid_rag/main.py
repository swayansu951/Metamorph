import ollama
import re
# from hybrid_vector.HYBRID_SEARCH.multi_HybridSearch import hybrid_search_all
# from hybrid_vector.HYBRID_SEARCH.multi_bm25Search import bm25_search_all
# from hybrid_vector.HYBRID_SEARCH.HybridSearch import hybrid_search
# from HybridRetriever.reranker import rerank
# from hybrid_vector.HYBRID_SEARCH.context_builder import build_context
from backend.retrievals.hybrid_rag.database.ingest_pdf import ingest_pdf
import os
from backend.retrievals.hybrid_rag.MUTI_GENERATE import multi_generate
from backend.retrievals.hybrid_rag.GENERATE import generate 

def main():
    """The main responce generater (the LLM responce), output responce accroding to the retrieved the chunks"""

    rag = generate()
    multi_rag = multi_generate()

    files=[]
    if not os.path.exists("rag_db"):
        os.makedirs("rag_db", exist_ok=True)

    doc_id = None

    text = input("\nEnter your question(else 'bye' to exit): ").strip()
    
    if "add pdf" in text:
        pdf = input("\nEnter PDF file with .pdf extension: ").strip()
        if pdf.endswith(".pdf"):
            doc_id = os.path.splitext(pdf)[0]
            ingest_pdf(pdf, doc_id)
            print(f"[+] PDF : {pdf}\n doc_id : {doc_id} \nindexed successfully.")
        else:
                print("[-] Invalid PDF file.")
    else:
        while True:
            try:
                if "bye" in text:
                    break
                try:
                    if not os.listdir("rag_db/documents"):
                        print("[-] No documents found in dataset")
                    for token in rag.generate(text, doc_id):
                        print(f"\nResearcher: ", token, end="", flush=True)
                except Exception as e:
                     return f"Error: {e}"
                
            except Exception as e:
                print(f"Error: {e}")
            if not os.listdir("rag_db/documents"):
                    print("[-] No documents found in dataset")

if __name__ == "__main__":
    main()
    
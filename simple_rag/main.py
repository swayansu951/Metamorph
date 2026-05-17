import os
import re
import ollama
from dotenv import load_dotenv
from huggingface_hub import login
from simple_rag.context_builder import build_context
from simple_rag.database.ingest_db import ingest_pdf
from simple_rag.retriever.chunk_retriever import Chunk_retriever

load_dotenv()
token = os.getenv("HF_TOKEN")

if token:
    login(token=token)
else:
    print("[-] WARNONG::Invalid credentials: 404 token not found!")
    
class GENERATE:
    prompt = """
            Answer the question using the context below. If the answer is not found in the context, say "I don't know".
            """
    def __init__(self):
        self.messages = [{'role': 'system', 'content': self.prompt}]

    def retrieve_context(self, query, doc_id):
        # text retrieval
        retriever = Chunk_retriever(doc_id)
        contexts = retriever.retrieve_chunks(query=query)
        context_text = build_context(contexts)

        context = f"""
        TEXT CONTEXT :
        {context_text}
        """
        return context

    def generate(self, user_input:str,doc_id):
        
        context = self.retrieve_context(user_input,doc_id)

        question_prompt = f"""
        Context:
        {context}
        Question:
        {user_input}
        """
        self.messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": question_prompt},
        ]

        response = ollama.chat(model='llama3.2:3b', 
                               messages=self.messages, 
                               stream=True, 
                               options={'num_gpu':-1,
                                        }, 
                               keep_alive=3,
                               )

        for chunk in response:
            content = chunk.get("message", {}).get("content", "")
            if not content:
                continue

            final_text = re.sub(r'\[.*?\]', '', content)
            if final_text:
                yield final_text

# CLI interface only..
def main():
    rag = GENERATE()
   
    files=[]
    if not os.path.exists("rag_db"):
        os.makedirs("rag_db", exist_ok=True)

    doc_id = None

    
    user = input("\nWant to add file?(yes/no): ").strip()
    
    if "yes" in user:
        pdf = input("\nEnter PDF file with .pdf extension: ").strip()
        if pdf.endswith(".pdf"):
            doc_id = os.path.splitext(pdf)[0]
            ingest_pdf(pdf, doc_id)
            print(f"[+] PDF {pdf} indexed successfully.")
        else:
                print("[-] Invalid PDF file.")
    elif "no" in user:
        if not os.listdir("rag_db/documents"):
                print("[-] No documents found in dataset")
        doc_id = input("\nEnter the document id to use: ")
        if not doc_id:
            doc_id = input("enter valid one: ")

    while True:
        try:
            text = input("\nEnter your question(else 'bye' to exit): ").strip()

            if "bye" in text:
                break
            print("\nResearcher: ", end="", flush=True)
            response_started = False

            for token in rag.generate(text, doc_id):
                response_started = True
                print(token, end="", flush=True)

            if response_started:
                print()
            else:
                print("No response generated.")
        
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
    

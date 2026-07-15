import ollama
import re
from HYBRID_SEARCH.HybridSearch import hybrid_search
from HybridRetriever.reranker import rerank
from HYBRID_SEARCH.context_builder import build_context
from database.ingest_pdf import ingest_pdf
from ModelnPrompt import MODELS, SYSTEM_PRMOPTS

class GENERATE:
    prompt = SYSTEM_PRMOPTS.rag_answer
    def __init__(self):
        self.messages = [{'role': 'system', 'content': self.prompt}]

    def retrieve_context(self, query, doc_id):
        """Retrieve the relevent context accroding to the user's query"""

        candidates = hybrid_search(query,doc_id)
        reranked = rerank(query, candidates)
        context = build_context(reranked)
        
        return context

    def generate(self, user_input:str,doc_id):
        """Generate the LLM responce after retrievning the requeried context according to the query,
           to send it as a proper output to the user"""

        context = self.retrieve_context(user_input,doc_id)

        prompt = f"""
        Answer the question using the context below. 
        If the answer is not found in the context, give a summary of the document".
        Context:
        {context}
        Question:
        {user_input}
        """
        self.messages.append({"role":"user","content":prompt})

        response = ollama.chat(model=MODELS.rag_model, messages=self.messages, stream=True, options={"num_thread":10,"keep_alive":10})
        full_response = ""
        sentence_buffer = ""

        for chunk in response:
            content = chunk['message']['content']
            full_response += content
            sentence_buffer += content

            if any(p in content for p in [".","!","?","*","\n"]):
                    text_to_speak = re.sub(r'\[.*?\]', '', sentence_buffer).strip()

                    if text_to_speak:
                        yield str(text_to_speak)
                    sentence_buffer= ""

        if sentence_buffer.strip():
                final_text = re.sub(r'\[.*?\]', '', sentence_buffer).strip()
                if final_text:
                    yield final_text


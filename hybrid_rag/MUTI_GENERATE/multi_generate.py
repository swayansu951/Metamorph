import ollama
import re
from HYBRID_SEARCH.multi_HybridSearch import hybrid_search_all
from HybridRetriever.reranker import rerank
from HYBRID_SEARCH.context_builder import build_context
from database.ingest_pdf import ingest_pdf
from ModelnPrompt import MODELS, SYSTEM_PRMOPTS
import os


class MULTI_GENERATE:
    prompt = SYSTEM_PRMOPTS.rag_answer
    def __init__(self):
        self.messages = [{'role': 'system', 'content': self.prompt}]
    
    def multi_retrieve_context(self, query):
        """To retrieve all the context using hybrid search"""

        candidates = hybrid_search_all(query)
        if not candidates:
            return ""

        reranked = rerank(query, candidates)
        context = build_context(reranked)
        return context
         
    def multi_generate(self, user_input:str):
        """To generate multiple responce from multiple retrieved context"""
        
        context = self.multi_retrieve_context(user_input)

        prompt = f"""
        Answer the question using the context below. 
        If the answer is not found in the context, give a summary of the document".
        Context:
        {context}
        Question:
        {user_input}
        """
        self.messages.append({"role":"user","content":prompt})

        response = ollama.chat(model=MODELS.rag_model, messages=self.messages, stream=True, options={"num_thread":10,"keep_alive":"10s"})
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

from simple_rag.main import GENERATE
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage

generator = GENERATE()
system_prompt = SystemMessage("Answer the question using the context below. If the answer is not found in the context or not relevant or no document uploaded, use web crawling to get answer'")

def make_rag_tool(doc:str):
    @tool
    def RAG_router(query):
        """uses the RAG architecture to search answer from a given document"""
        
        context = generator.retrieve_context(query, doc)
        if not context or not context.strip() : return "No_Relevent_Context"

        return context
    
    return RAG_router
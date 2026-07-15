from simple_rag.main import GENERATE
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from ModelnPrompt import SYSTEM_PRMOPTS

generator = GENERATE()
system_prompt = SystemMessage(SYSTEM_PRMOPTS.rag_answer)

@tool
def RAG_router(query: str, doc_id: str) -> str:
    """Uses the RAG architecture to retrieve context from an uploaded document."""

    context = generator.retrieve_context(query=query, doc_id=doc_id)
    if not context or not context.strip():
        return "WEB_SEARCH" # use WEB_SEARCH instead

    return context

def make_rag_tool(doc:str):
    @tool
    def RAG_router(query):
        """uses the RAG architecture to search answer from a given document"""
        
        context = generator.retrieve_context(query, doc)
        if not context or not context.strip() : return "WEB_SEARCH" # use web search instead

        return context
    
    return RAG_router

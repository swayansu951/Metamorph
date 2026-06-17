from typing import Dict, List, Any
from langchain_core.messages import HumanMessage
from langchain_ollama.chat_models import ChatOllama
from .uuid_registry import REGISTRY

model = "llama3.2:3b"
agent_name = "web_llm_generator"
id = REGISTRY.get_or_create_agent(agent_name)
REGISTRY .task_counts(agent_name) 

class WEB_LLM:
    def __init__(self):
        self.model = model   

    def LLM_RESPONSE(self,query:str, data:List[Dict], id:Any = id) -> str:
        context = "\n\n".join(
            f"Source: {item.get('source_url', '')}\n"
            f"Title: {item.get('title', '')}\n"
            f"Content: {item.get('chunk') or item.get('media_text', '')}"
            for item in data
        )

        PROMPT = f"""
            You are an expert content extractor.
            Answer the user's query using only the retrieved web context below.
            If the context is insufficient, say that clearly.
            Include relevant source URLs when available.

            User query:
            {query}

            Retrieved context:
            {context}
        """
        
        llm = ChatOllama(
            model=model,
            stream=True,
            num_gpu = -1,
            temperature = 0.1,
            keep_alive=6,
        )
        response_parts = []
        for chunk in llm.stream(PROMPT):
            content = getattr(chunk, "content", "") or ""
            # print(content, end="", flush=True)
            response_parts.append(content)

        return "".join(response_parts)

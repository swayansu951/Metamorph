import json
from pathlib import Path
from typing import Dict, List, Any
from .uuid_registry import REGISTRY, uuidInfo
from langchain_ollama.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_services.ModelnPrompt import MODELS, SYSTEM_PRMOPTS

model = MODELS.web_model
agent_name = "web_llm_generator"
id = REGISTRY.get_or_create_agent(agent_name)
REGISTRY.task_counts(agent_name)

class WEB_LLM:
    def __init__(self, path = "uuid_registry"):
        self.model = model
        

    def _collect_image_urls(self, data: List[Dict]) -> List[str]:
        image_urls = []
        seen = set()

        for item in data:
            images = item.get("image") or item.get("media_url")
            if not images:
                continue
            if isinstance(images, str):
                images = [images]

            for url in images:
                if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                    continue
                if url in seen:
                    continue
                seen.add(url)
                image_urls.append(url)

        return image_urls[:3]

    def _format_image_markdown(self, data: List[Dict], image_urls: List[str]) -> str:
        if not image_urls:
            return ""

        titles_by_url = {}
        for item in data:
            title = item.get("title") or "Retrieved image"
            images = item.get("image") or item.get("media_url")
            if isinstance(images, str):
                images = [images]
            for url in images or []:
                titles_by_url.setdefault(url, title)

        image_lines = [
            f"![{titles_by_url.get(url, 'Retrieved image')}]({url})"
            for url in image_urls
        ]
        return "\n\nRelevant images:\n" + "\n".join(image_lines)

    def LLM_RESPONSE(self, query: str, data: List[Dict], id: Any = id) -> str:
        """Final LLM response."""
        image_urls = self._collect_image_urls(data)

        context = "\n\n".join(
            f"Source: {item.get('source_url', '')}\n"
            f"Title: {item.get('title', '')}\n"
            f"Content: {item.get('chunk') or item.get('media_text', '')}\n"
            f"Images: {', '.join(item.get('image') or []) if isinstance(item.get('image'), list) else item.get('image', '')}\n"
            for item in data
        )

        prompt = [
            SystemMessage(content=SYSTEM_PRMOPTS.web_answer),
            HumanMessage(content=f"""
                User query:
                {query}

                Retrieved context:
                {context}
            """),
        ]

        llm = ChatOllama(
            model=self.model,
            stream=True,
            num_gpu=-1,
            temperature=0.1,
            keep_alive=1,
        )
        response_parts = []
        for chunk in llm.stream(prompt):
            content = getattr(chunk, "content", "") or ""
            # print(content, end="", flush=True)
            response_parts.append(content)
        
        REGISTRY.save_details()

        return "".join(response_parts).strip() + self._format_image_markdown(data, image_urls)



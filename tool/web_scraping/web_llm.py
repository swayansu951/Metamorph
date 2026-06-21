import re
import climage
import requests
from PIL import Image
from typing import Dict, List, Any
from .uuid_registry import REGISTRY
from langchain_core.messages import HumanMessage
from langchain_ollama.chat_models import ChatOllama

model = "gemma4-e4b_q4_k_m"
agent_name = "web_llm_generator"
id = REGISTRY.get_or_create_agent(agent_name)
REGISTRY .task_counts(agent_name) 

class WEB_LLM:
    def __init__(self):
        self.model = model   

    def include_image(self, urls:str):
        if not urls: return
        if isinstance(urls, str):
            urls = [urls]

        for url in urls:
            try:
                img_data = requests.get(url, stream=True)
                img = Image.open(img_data.raw)
                # Convert and print directly to the CLI window
                output = climage.convert_pil(img, is_unicode=True)
                print(output)
            except Exception as e:
                print("error", str(e))

    def LLM_RESPONSE(self,query:str, data:List[Dict], id:Any = id) -> str:
        """Final LLM response"""
        image_urls = []
        for item in data:
            image = item.get("image")
            if image:
                if isinstance(image, list):
                    image_urls.extend(image)  # flatten list
                elif "image" in item and item.get("image"):
                    image_urls.append(image)
        for url in image_urls:
            meida = url

        context = "\n\n".join(
            f"Source: {item.get('source_url', '')}\n"
            f"Title: {item.get('title', '')}\n"
            f"Content: {item.get('chunk') or item.get('media_text', '')}\n"
            for item in data
        )

        PROMPT = f"""
            You are an expert content extractor.
            Answer the user's query using only the retrieved web context below.
            If the context is insufficient, say that clearly.
            Include relevant source URLs when available.
            If the images are relevant, describe them. If they are not relevant, ignore them.
            Correctly separating the sentnces and the nextlines to make the context more user readable.
            for image use:
            {self.include_image(url)}
            
            User query:
            {query}

            Retrieved context:
            {context}
        """
        
        llm = ChatOllama(
            model=self.model,
            stream=True,
            num_gpu = -1,
            temperature = 0.1,
            keep_alive=6,
            iamges = image_urls,
        )

        response_parts = []
        for chunk in llm.stream(PROMPT):
            content = getattr(chunk, "content", "") or ""
            print(content, end="", flush=True)
            response_parts.append(content)

        # for url in image_urls:
        #     self.include_image(url)
        
        return "".join(response_parts)

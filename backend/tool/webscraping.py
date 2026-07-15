# Advanced web crawling technique...
# Dedicates on high performance with high quality and accurate retrieval.
# No case of halucination and misliding of information.
"""crawl4ai, web crawler tool"""
import re
import json
import torch
import ollama
import asyncio
from pathlib import Path
from llama_cpp import llama
from pydantic import BaseModel
from langchain_core.tools import tool
from crawl4ai.async_configs import CacheMode
from ddgs import DDGS
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode, LLMExtractionStrategy, LLMConfig
from crawl4ai.deep_crawling.filters import URLPatternFilter, DomainFilter, ContentRelevanceFilter
from llm_services.ModelnPrompt import MODELS, SYSTEM_PRMOPTS


USE_LOCAL_SYSTEM = True

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

iamge_path = Path("./images/")
reranker_model = None

LOCAL_LLM = None

def get_reranker_model():
    """Load the reranker only when web fallback actually runs."""

    global reranker_model
    if reranker_model is None:
        from sentence_transformers import CrossEncoder

        device = "cuda" if torch.cuda.is_available() else "cpu"
        reranker_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device=device)
    return reranker_model
    
async def web_scrape(url:list) -> list:
    """scrap web pages using a headless browser to retireve web content"""

    browser_config = BrowserConfig(headless=False,  # keep it false  to visually watch what the crawler is actually seeing when it navigates to your target URLs.
                                   extra_args=["--disable-blink-features=AutomationControlled"]
                                   )
    
    run_config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=True,
            options={'strip_link' : True}),
            cache_mode=CacheMode.BYPASS,
            stream=True
            )
    scraped_pages = []
    async with AsyncWebCrawler(config= browser_config) as crawler:
        results = await crawler.arun_many(config=run_config, 
                                          urls=url)
        if hasattr(results, "__aiter__"):
            async for result in results:
                if result.success:
                    scraped_pages.append({"url" : getattr(result, "url", ""), "content" : result.markdown.fit_markdown}
                                         )
        else:
            for result in results:
                if result.success:
                    scraped_pages.append({"url" : getattr(result, "url", ""), "content" : result.markdown.fit_markdown}
                                         )
    
    return scraped_pages

def reranker(query: str, crawled_data: list):
    """rerank the response from the web though scoring to retrieve highest precision text"""

    candidates = []
    for pages in crawled_data:
        url_header = f"[source doc context : {pages['url']}]\n"
        paragraphs = [
            p.strip() for p in pages["content"].split("\n\n") if len(p.strip()) > 40     
        ]
        
        for para in paragraphs:
            candidates.append({"text" : f"{url_header}{para}"})
    
    if not candidates:
        return []
    
    # calculate attention matrix score
    pair = [[query, item["text"]] for item in candidates[:25]]

    with torch.no_grad():
        score = get_reranker_model().predict(pair)

    ranked_indices = sorted(range(len(score)), key=lambda i: score[i], reverse=True)
    return [candidates[idx]["text"] for idx in ranked_indices[:3]]

def generate_response(query:str, context:list):
    """VLM response"""
    unified_context = "source".join(context)
    SYSTEM_PROMPT = SYSTEM_PRMOPTS.web_extractor
    USER_PROMPT = (
                    f"context :\n {unified_context}\n\n Query : \n {query}\n\n return json output: "
    )
    
    FULL_PROMPT = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{SYSTEM_PROMPT}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n{USER_PROMPT}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
    
    response = ollama.chat(model=MODELS.vision_model,
                           images=[iamge_path], 
                            stream=True, 
                            think="medium", 
                            options={"temperature" :0.1,
                                    "num_ctx" : 4150,
                                    "num_predict" : 512,
                                    'num_gpu' : -1,
                                    },
                            prompt=FULL_PROMPT,
                            keep_alive=3,
                            )

    for chunk in response:
        for chunk in response:
            content = chunk.get("message", {}).get("content", "")
            if not content:
                continue

            final_text = re.sub(r'\[.*?\]', '', content)
            if final_text:
                yield final_text

async def run_pipeline(query: str, url:dict): # set pre defined urls to use only not more that that, change: url
    """Runs the webscraping pipeline to retrieve information according to the users query
        1. set the query : str with hardcoded url : dict in dictionary format separating the different types of urls based on task
        2. run reranker funcion as output and connect to the llm for final response
    """
    
    # ::: STEP1 ::: 
    raw_data = await web_scrape(url=url)

    combined_text = []

    for page in raw_data:
        content = page.get("content","")
        source_url = page.get("url","")

        if content:
            combined_text.append(
                f"source : {source_url}\n {content[:4150]}"
            )
    
    return "\n\n".join(combined_text)[:6000]

# hard code the web pages to scrap 
# user query
# function call using asyncio.run(...)


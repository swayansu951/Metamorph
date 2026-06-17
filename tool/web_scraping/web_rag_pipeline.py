"""Conect every functions in a pipeline systematic way:\n
    1. query_filter\n
    2. DDGS_finder\n
    3. BS4Scraper\n
    4. searchDBn\n
    5. LLM_response\n
    
    In between query_filter and every small agent call the uuid_register is called to register the agent id
    Semantic chunker is called inside the searchDB 
"""
from typing import TypedDict, Dict, List, Optional, Any
from .DDGS_finder import DDGSSearch
from .BS4Scraper import bs4scraper
from .searchDB import searchDB
from .query_filer import filter
from . import duckduckgo
from .web_llm import WEB_LLM


class pipelineState(TypedDict):
    query : str
    response : str
    filtered_query : Dict
    search_result : List[Dict]
    scraped_result : List[Dict]
    retrieved_content : List[Dict]
    stored_result : List[Dict]

class PIPELINE:
    def __init__(self):
        self.store_scraper = searchDB()# stores the scraped page in the database
        self.bs4_scraper = bs4scraper()# web page scraper bs4
        self.ddgs_finder = DDGSSearch()# url search, filter with ddgs
        # self.safe_search = duckduckgo()# search filter to get safe domains
        self.query_filter = filter()# filter the query into format 
        self.web_llm = WEB_LLM()# after all the extraction and storage, the data goes to llm and then give a response
        # self.ddgs_search = duckduckgo()# ddgs for news search, media seach

    def pipeline(self, payload:pipelineState) -> str:
        payload["scraped_result"] = [] # to prevent from keyError if something get like {"query" :  "something.."}
        payload["stored_result"] = []# to prevent from keyError if something get like {"query" :  "something.."}
        payload["retrieved_content"] = []
        payload["search_result"] = []
        payload["response"] = ""
        filtered = self.query_filter.query_filer({
            "query" : payload["query"],
            "output" : {},
            "agent_id" : ""
            })
        
        payload["filtered_query"] = filtered["output"] # store in filtered query
        payload["filtered_query"].setdefault("query", payload["query"])
        payload["filtered_query"].setdefault("original_query", payload["query"])

        payload["search_result"] = self.ddgs_finder.search(payload["filtered_query"]) # search result from the filtered query, safe search is already applied inside the search function 

        for result in payload["search_result"]:
            if result["result_type"] not in {"text", "news"}: continue
            page = self.bs4_scraper.soupscraper(result["url"]) # catch the urls only

            if not page:continue

            page["rank"] = result.get("rank") # get the ranks from it...
                
            payload["scraped_result"].append(page) # get all the required dict type into it..
            
            storage_result = self.store_scraper.scrape_page(data=page, query=payload["query"])
            payload["stored_result"].append(storage_result)

        payload["retrieved_content"] += self.store_scraper.hybrid_search(query=payload["query"])# use by default top 6 retriever logic according to the user query
        if not payload["retrieved_content"]:
            payload["response"] = "I could not retrieve enough web context to answer reliably."
            return payload["response"]
        payload["response"] += self.web_llm.LLM_RESPONSE(data=payload["retrieved_content"], query=payload["query"])

        return payload["response"]

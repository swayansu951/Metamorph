"""DDGS url filtering for search module\n
    function :\n
     search\n"""
from datetime import datetime
import random
import time
from ddgs import DDGS
from typing import Callable, Dict, List, Any
from web_scraping.duckduckgo import safe_search, TRUSTED_SITES
from urllib.parse import urlparse

class DDGSSearch:
    """function:\n
        - search\n
        It stores the data retrieved in the json format, more info in the search function -->"""
    def __init__(self, timeout:int = 10, max_retries:int = 2, backoff:float = 2.0) ->int:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff

    def _depth_max_result(self, search_depth:str) -> int:
        """makes how deep the search should happen\n 
        quick, moderate, deep\n"""
        if search_depth == "quick":
            return 3
        elif search_depth in ["medium", "moderate"]:
            return 5
        elif search_depth == "deep":
            return 8
        return 3
    
    def _timelimit(self, freshness:str) -> str:
        """how fresh the data should be retrieved\n
            latest, recent, historical\n"""
        if freshness == "latest":
            return "d"
        elif freshness == "recent":
            return "m"
        elif freshness == "historical":
            return "y"
        return None
    
    def _modes(self,payload : Dict[str, Any] ) ->List[str]:
        """selects the mode of response:\n
            default: text\n
            news | image | video"""
        query_type = payload.get('query_type', 'text_only')
        domain = payload.get('domain', 'general')
        media_need = payload.get('media_need', 'none')

        mode = ['text']

        if domain == 'news':
            mode.append('news')
        
        if query_type in ['image_needed','mixed'] or (
            media_need == 'required' and query_type != 'video_needed'
        ):
            mode.append('image')
        
        if query_type in ['video_needed','mixed']:
            mode.append('video')
        
        return list(dict.fromkeys(mode))

    def _search_with_backoff(self, search_call: Callable[[], Any]) -> list:
        """Run one DDGS call with light retry/backoff for temporary rate limits."""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return list(search_call())
            except Exception as e:
                last_error = e
                message = str(e).lower()
                is_rate_limit = "ratelimit" in message or "403" in message
                if attempt >= self.max_retries or not is_rate_limit:
                    raise
                delay = self.backoff * (2 ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(delay)
        raise last_error

    def _error_result(self, result_type: str, error: Exception, site: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result_type" : "Error",
            "failed_mode" : result_type,
            "title" : "DDGS Error",
            "url" : None,
            "snippet" : str(error),
            "rank" : 0,
            "source" : "ddgs",
            "site" : site,
        }

    def _query_candidates(self, payload: Dict[str, Any]) -> List[str]:# test one if not correct fall back to previous commit
        """Build conservative fallback queries when the filtered query is too narrow."""
        query = payload.get("query", "").strip()
        original_query = payload.get("original_query", "").strip()
        domain = payload.get("domain", "general")

        candidates = []
        for item in [query, original_query]:
            if item and item not in candidates:
                candidates.append(item)

        if "." in query:
            expanded = query.replace(".", " ").strip()
            if expanded and expanded not in candidates:
                candidates.append(expanded)

        if query:
            docs_query = f"{query} documentation"
            if docs_query not in candidates:
                candidates.append(docs_query)

            if domain == "programming":
                github_query = f"{query} github"
                if github_query not in candidates:
                    candidates.append(github_query)

        return candidates or [query]    
    
    def _is_allower_url(self, url:str) -> bool:

        hostname = (urlparse(url).hostname or "").lower()
        hostname = hostname.removeprefix("www.")

        for domain in TRUSTED_SITES:
            domain = domain.removeprefix("www.").strip().lower()
            if hostname == domain or hostname.startswith(f".{domain}"): return True

        return False

    def search(self, payload : Dict[str, Any]) -> list[Dict[str, Any]]:
        """Search function using DDGS for url filtering. \n
            **input structure:** \n
            ***Output of the query_filter***\n
            "query" : "user provided query, over here..."\n
            "query_type" : "query type here..."\n
            "domain" : "which domain the answer sohould be, over here..."\n
            "freshness" : "how aged the qeury looks should be, over here..."\n
            "source_quality" : "from which type of source should the answer retrieve from, over here..."\n
            "media_need" : "whether the retrieval need image according to the query given or not, over here.."\n
            "search_depth" : "how deep the retrieval should be according to the query, over here..."\n
            **Output :**\n
                result_type:\n
                title:\n
                url:\n
                snippet:\n
                media_url:\n
                rank:\n
                source:\n
                date:\n
                thumbnail:\n
                duration:\n
            Example: \n
                query_info = {
                    "query": "CNN architecture diagram",
                    "query_type": "image_needed",
                    "domain": "science",
                    "freshness": "stable",
                    "source_quality": "academic",
                    "media_need": "required",
                    "search_depth": "quick"
                }

                finder = DDGSFinder()
                results = finder.search(query_info)

                for r in results:
                    print(r)
            
        """
        site_filter = " OR ".join(f"site:{domain.strip()}" for domain in TRUSTED_SITES)
        
        site = {"allowed_domains" : TRUSTED_SITES}
        query = payload['query']
        query_candidates = self._query_candidates(payload)
        max_depth = payload.get('search_depth', 'quick')
        freshness = payload.get('freshness', 'recent')
        max_result = self._depth_max_result(search_depth=max_depth)
        timelimit = self._timelimit(freshness)
        modes = self._modes(payload)

        output = []
        try:
            with DDGS(timeout=self.timeout) as ddgs:
                if "text" in modes:
                    text_error = None
                    searched_query = query
                    try:
                        results = []
                        for candidate in query_candidates:
                            search_query = f"{candidate} ({site_filter})"
                            results = self._search_with_backoff(lambda search_qery=search_query : ddgs.text(
                                query=search_query,
                                max_results=max_result,
                                timelimit=timelimit,
                            ))
                            results = [
                                        item for item in results
                                        if self._is_allower_url(item.get("href", ""))
                                    ]
                            if results:
                                break
                    except Exception as e:
                        text_error = e
                        results = []

                    if not results and text_error:
                        output.append(self._error_result("text", text_error, site))

                    for rank, item in enumerate(results, start=1):
                        output.append(
                            {   "date" : datetime.now(),
                                "result_type" : "text",
                                "title" : item.get("title", ""),
                                "url" : item.get('href', ''),
                                "snippet" : item.get('body',''),
                                "media_url" : None,
                                "rank" : rank,
                                "source" : "ddgs",
                                "searched_query" : searched_query,
                                "site" : site
                            }
                        )
                
                if "news" in modes:
                    news_query = f"{query} ({site_filter})"
                    try:
                        results = self._search_with_backoff(lambda: ddgs.news(
                        query=news_query,
                        max_results=max_result,
                        timelimit=timelimit,
                        ))
                        results = [item for item in results if self._is_allower_url(item.get("url", ""))]
                    except Exception as e:
                        output.append(self._error_result("news", e, site))
                        results = []

                    for rank, item in enumerate(results, start=1):
                        output.append(
                            {   "date" : item.get("date",''),
                                "result_type" : "news",
                                "title" : item.get("title", ""),
                                "url" : item.get('url', ''),
                                "snippet" : item.get('body',''),
                                "media_url" : item.get('image',None),
                                "rank" : rank,
                                "source" : "ddgs",
                                "site" : site
                            }
                        )

                if "image" in modes:
                    try:
                        results = self._search_with_backoff(lambda: ddgs.images(
                        query=query,
                        max_results=max_result,
                        ))
                    except Exception as e:
                        output.append(self._error_result("image", e, site))
                        results = []

                    for rank, item in enumerate(results, start=1):
                        output.append(
                            {   "date" : datetime.now(),
                                "result_type" : "image",
                                "title" : item.get("title", ""),
                                "url" : item.get('url', ''),
                                "snippet" : None,
                                "media_url" : item.get('image',None),
                                "thumbnail" : item.get("thumbnail", ""),
                                "rank" : rank,
                                "source" : "ddgs",
                                "site" : site
                            }
                        )
                
                if "video" in modes:
                    try:
                        results = self._search_with_backoff(lambda: ddgs.videos(
                        query=query,
                        max_results=max_result,
                        ))
                    except Exception as e:
                        output.append(self._error_result("video", e, site))
                        results = []

                    for rank, item in enumerate(results, start=1):
                        output.append(
                            {   "date" : datetime.now(),
                                "result_type" : "video",
                                "title" : item.get("title", ""),
                                "url" : item.get('content', ''),
                                "snippet" : item.get('description',''),
                                "media_url" : item.get('image',None),
                                "duration" : item.get("duration",""),
                                "rank" : rank,
                                "source" : "ddgs",
                                "site" : site
                            }
                        )
        except Exception as e:
            return [{
                "result_type" : "Error",
                "title" : "DDGS Error",
                "url" : None,
                "snippet" : str(e),
                "rank" : 0,
                "source" : "ddgs",
                "site" : site
            }]    
        
        return output

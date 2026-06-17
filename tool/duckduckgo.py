from ddgs import DDGS
from urllib.parse import urlparse

TRUSTED_SITES = [
    "wikipedia.org",
    "github.com",
    "stackoverflow.com",
    "reuters.com",
    "nasa.gov",
    "youtube.com",
]

def safe_search(query:str) -> str:
    """Defines which domains to use only, with safe query and data extraction safety.
        retrieves each domain according to the query and fetch one by one from them
    """
    choosed_domains = "OR".join(f"site : {domains}" for domains in TRUSTED_SITES)
    return {
            "query": query,
            "domains" : (choosed_domains)
            }

def news_search(query: str, domains : tuple) -> dict[str]:
    """Gets a proper query format to search news.
        structure from LLM: 
        
        input = {
            query: "user search query in better form",
            domains : "use the domains only choosed",
            time : "starting time"
        }

        structure as output:

        output = {
            query: "text over here, only the search part",
            url: "url over here",
            result : "searched result over here",
            duration : "total time took to respond"
        }
        """
    with DDGS() as ddgs:
        search_result = []
        results = ddgs.news(keywords=query,
                           timelimit='d',
                           max_results=6)
        
        for articles in results:
            search_result.append({
                search_result["source"] : articles['source'],
                    search_result["time"] : articles['date'],
                    search_result["title"] : articles['title'],
                    search_result['urls'] : articles['url']
            })

            return search_result
        
def search_media(query:str, search_type :str, max_search :int = 3) -> list:
    """search for the video and image from the query directly to the webpage.
        structure from llm:
        input = {
            query : "image or video as per user query"
            search_type : "image"/"video"
            time : "starting time"
        }
        structure as output:
        output ={
            type : "image/video search to be performed"
            title : "what was that"
            media : "image or video searched"
            url : "url link of that source"
            duration : "if that was for video then only"
        }
        """
    
    if not query:
        return []
    
    try :
        with DDGS() as ddgs:
            formated_result = []
            if search_type == "image": # Extract image content only else move video 
                search_image = ddgs.images(query, max_results=max_search)
                for result in search_image: # Stores evry searched out results in the following format
                    formated_result.append(
                        {
                            "type" : "image",
                            "title" : result['title'],
                            "media" : result['image'],
                            "url" : result['url']
                        }
                    )
            elif search_type == "video": # Extract video content only 
                search_video = ddgs.videos(query, max_results=max_search)
                for result in search_video: # Stores evry searched out results in the following format
                    formated_result.append(
                        {
                            "type" : "video",
                            "title" : result['title'],
                            "media" : result['image'],
                            "url" : result['content'],
                            "duration": result['duration', ""]
                        }
                    )

            return formated_result
    except Exception as e:
        print(f"oops! somthing went wrong : {e}")
        return []
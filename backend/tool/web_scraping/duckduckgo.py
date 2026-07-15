from ddgs import DDGS
from urllib.parse import urlparse
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama.chat_models import ChatOllama
from .uuid_registry import REGISTRY
from typing import List, Dict, Any
from llm_services.ModelnPrompt import MODELS, SYSTEM_PRMOPTS

SPORTS_SITES = [
    "sofascore.com",
    "fbref.com",
    "formula1.com",
    "basketball-reference.com",
    "espn.com",
    "cbssports.com",
    "skysports.com",
    "cricbuzz.com",
    "espncricinfo.com",
]

TRUSTED_SITES = [
    "en.wikipedia.org",
    "pubmed.ncbi.nlm.nih.gov",
    "medlineplus.gov",
    "webmd.com",
    "healthline.com",
    "investing.com",
    "marketwatch.com ",
    "investopedia.com",
    "mayoclinic.org", # may contain adult things, so must be strictly maintained
    "wikipedia.org",
    "github.com",
    "stackoverflow.com",
    "reuters.com",
    "nasa.gov",
    "youtube.com",
    "reddit.com",
    "geeksforgeeks.org",
    "idss.mit.edu",
    "pubmed.ncbi.nlm.nih.gov",
    "ijmr.org.in",
    *SPORTS_SITES,
]
model = MODELS.query_router

def safe_search(query:str) -> List[Dict[str, Any]]:
    """Defines which domains to use only, with safe query and data extraction safety.\n
        retrieves each domain according to the query and fetch one by one from them
    """
    choosed_domains = " OR ".join(f"site:{domains}" for domains in TRUSTED_SITES)
    sites =[]

    PROMPT = [
        SystemMessage(content=SYSTEM_PRMOPTS.site_filter),
        HumanMessage(content=f"Trusted domains: {TRUSTED_SITES}\nUser query: {query}"),
    ]
    
    agent_name = "site_agent"
    id = REGISTRY.get_or_create_agent(agent_name)
    REGISTRY .task_counts(agent_name)
    data = ChatOllama(
        model=model,
        stream=False,
        num_gpu = -1,
        temperature = 0.1,
        keep_alive=6,
    )
    response = data.invoke(PROMPT)
    
    return {
        "agent_id" : id,
        "agent_name" : agent_name,
        "response" : response.content, # list of query + site. use the response only..
    }

def news_search(query: dict[list[str]]) -> list[str]:
    """Gets a proper query format to search news.
        structure from LLM: \n
        input = {\n
            query: "user search query in better form",\n
            time : "starting time"\n
        }\n
        structure as output:\n
        output = {\n
            query: "text over here, only the search part",\n
            url: "url over here",\n
            result : "searched result over here",\n
            duration : "total time took to respond"\n
        }\n
        """
    with DDGS() as ddgs:
        search_result = []
        results = [ddgs.news(query= item,
                           timelimit='d',
                           max_results=6)
                           for item in query["response"]
                    ]
        for articles in results:
            search_result.append({
                "source" : articles['source'],
                "time" : articles['date'],
                "title" : articles['title'],
                'urls' : articles['url']
            })

        return search_result
        
def search_media(query:str, search_type :str, max_search :int = 3) -> list:
    """search for the video and image from the query directly to the webpage.\n
        structure from llm:\n
        input = {\n
            query : "image or video as per user query"\n
            search_type : "image"/"video"\n
            time : "starting time"\n
        }\n
        structure as output:\n
        output ={\n
            type : "image/video search to be performed"\n
            title : "what was that"\n
            media : "image or video searched"\n
            url : "url link of that source"\n
            duration : "if that was for video then only"\n
        }\n
        """
    
    if not query:
        return []
    
    try :
        with DDGS() as ddgs:
            formated_result = []
            if search_type == "image": # Extract image content only else move video 
                search_image = [ddgs.images(query=item, max_results=max_search)
                                for item in query["response"]]
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
                search_video = [ddgs.videos(query=item, max_results=max_search)
                                for item in query["response"]]
                for result in search_video: # Stores evry searched out results in the following format
                    formated_result.append(
                        {
                            "type" : "video",
                            "title" : result['title'],
                            "media" : result['image'],
                            "url" : result['content'],
                            "duration": result.get('duration', "")
                        }
                    )

            return formated_result
    except Exception as e:
        print(f"oops! somthing went wrong : {str(e)}")
        return []

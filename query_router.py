import ollama
import asyncio
from simple_rag.main import GENERATE
from typing import TypedDict, Optional
from langchain_ollama import ChatOllama
from tool.webscraping import run_pipeline
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph,END,START
from typing import TypedDict, Annotated , Sequence
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage


class AgentState(TypedDict):
    messages : Annotated[Sequence[BaseMessage], add_messages]
    query : str
    doc_id : Optional[str]
    chunk_ids : list[int]
    cursor : int 
    window : int
    slide_window : int
    context : str
    current_window : str
    all_window : list[str]
    running_summary : str
    final_answer : str
    enough : bool
    use_web : bool
    source : str
    rest : int
    session_summary : str

# Simple RAG response generator
generator = GENERATE()

# widely used system prompt..
system_prompt = SystemMessage("Answer the question using the context below. If the answer is not found in the context or not relevant or no document uploaded, then use web crawling to get answer'")

# base message schema/structure..
messages = [{'role' : 'system' , 'content' : system_prompt}]

# Single unit controling model..
llm_model = ChatOllama(model='llama3.1:8b-instruct-q5_K_S', 
                        stream=True, 
                        num_gpu=0,
                        keep_alive=15,
                        num_thread=11,
                        temperature=0.1,
                        )

direct_llm_model = ChatOllama(model='llama3.2:3b', 
                        stream=True, 
                        num_gpu=-1,
                        keep_alive=3,
                        temperature=0.2,
                        )

# urls for web crwaling
URLS = {
    "finance": [
    ],
    "science": [
        "https://arxiv.org",
        "https://nasa.gov",
        "https://usgs.gov",
    ],
    "news": [
        "https://www.reuters.com",
        "https://apnews.com",
    ],
    "health": [
        "https://cdc.gov",
        "https://who.int",
    ],
    "legal": [
        "https://indiacode.nic.in",
        "https://govinfo.gov",
    ],
}

# preserve the context window and accuracy increase LangGraph
class AgentState2(TypedDict):
    query : str
    doc_id : Optional[str]
    chunk_ids : list[int]
    cursor : int 
    window : int
    context : str
    current_window : str
    all_window : list[str]
    running_summary : str
    final_answer : str
    enough : bool
    use_web : bool
    rest : int

def direct_answer(state: AgentState) -> AgentState:
    """Direct llm response carried by it and generate response"""

    prompt = f"""
Answer the user normally and briefly.
If they ask about a PDF but no document is selected, tell them to upload/select a PDF first.

User: {state["query"]}
"""
    response = direct_llm_model.invoke([HumanMessage(content=prompt)]).content
    return {"final_answer": response}

def prepare_rag_windows(state:AgentState) -> AgentState:
    """"prepares the chunk window and the window split from the retireved context.
        1. Set the window size, e.g. 4000 from the original context retrieved.
        2. Slider window to be 10 - 15 % of the window size.
        3. set the cursor original pointer at 0.
        4. Set the current window be the slider window which feed the context to the LLM.
    """
    context = generator.retrieve_context(query=state["query"], doc_id=state["doc_id"])
    window = state.get("window", 4050)
    slider_window = state.get("slide_window", int(window * 0.15))

    spliter = RecursiveCharacterTextSplitter(
                                    chunk_size = window,
                                    chunk_overlap = slider_window,
                                    separators=["\n\n","\n"," ",""],
                                )
    windows = spliter.split_text(context)
    
    return {
    "context": context,
    "window": window,
    "slide_window": slider_window,
    "cursor": 0,
    "all_window": windows,
    "current_window": windows[0] if windows else "",
    "source": "rag",
    "rest": window - slider_window
    }
# To get a asyncio and safe web search result fit to the websearch tool writen(async function)
def select_web_category(query: str) -> str:
    """Select the most relevant URL category for web search."""

    normalized_query = query.lower()
    category_keywords = {
        "finance": [
            "stock", "market", "earnings", "revenue", "finance", "investment",
            "sec", "bank", "gdp", "inflation", "company", "shares",
        ],
        "science": [
            "research", "paper", "study", "science", "space", "nasa",
            "arxiv", "earthquake", "climate", "physics", "ai",
        ],
        "news": [
            "news", "latest", "current", "today", "recent", "breaking",
            "update", "updates", "anthropic", "openai", "google", "microsoft",
        ],
        "health": [
            "health", "disease", "medical", "medicine", "virus", "covid",
            "cdc", "who", "symptoms", "vaccine",
        ],
        "legal": [
            "law", "legal", "act", "regulation", "policy", "court",
            "government", "bill", "compliance",
        ],
    }

    scores = {
        category: sum(keyword in normalized_query for keyword in keywords)
        for category, keywords in category_keywords.items()
    }
    best_category = max(scores, key=scores.get)
    return best_category if scores[best_category] > 0 else "news"


def _stringify_context(context) -> str:
    """checks and handle mulultiple query input type without throughing error for the web_query"""

    if context is None:
        return ""
    if isinstance(context, str):
        return context
    try:
        return "".join(str(part) for part in context)
    except TypeError:
        return str(context)

async def _run_web_pipeline(query: str) -> str:
    """run asyncio web search pipeline"""

    selected_category = select_web_category(query)
    selected_urls = URLS[selected_category]

    if hasattr(run_pipeline, "ainvoke"):
        context = await run_pipeline.ainvoke({"query": query, "url": selected_urls})
    else:
        context = await run_pipeline(query, url=selected_urls)
    return _stringify_context(context)

async def add_to_web(state:AgentState) -> AgentState:
    """call add_to_web if the evaluator directs to 'WEB_SEARCH' to get more clarity answer from the user's query"""
    context = await _run_web_pipeline(state["query"])
    
    combined_context = f"{state.get('context', '')}\n\n{context}".strip()
    window = state.get("window", 4150)
    slider_window = state.get("slide_window", int(window * 0.15))
    spliter = RecursiveCharacterTextSplitter(
                                    chunk_size = window,
                                    chunk_overlap = slider_window,
                                    separators=["\n\n","\n"," ",""],
                                )
    windows = spliter.split_text(combined_context)

    return {
    "context": combined_context,
    "window": window,
    "slide_window": slider_window,
    "cursor": 0,
    "all_window": windows,
    "current_window": windows[0] if windows else "",
    "source": "web",
    "rest": window - slider_window
    }

async def web_search(state:AgentState) -> AgentState:
    """call web_search tool for retireve information from web if no document or less precise info in document"""
    
    context = await _run_web_pipeline(state["query"])
    
    window = state.get("window", 4150)
    slider_window = state.get("slide_window", int(window * 0.15))

    spliter = RecursiveCharacterTextSplitter(
                                    chunk_size = window,
                                    chunk_overlap = slider_window,
                                    separators=["\n\n","\n"," ",""],
                                )
    windows = spliter.split_text(context)

    return {
    "context": context,
    "window": window,
    "slide_window": slider_window,
    "cursor": 0,
    "all_window": windows,
    "current_window": windows[0] if windows else "",
    "source": "web",
    "rest": window - slider_window
    }

def reason_over_window(state:AgentState) -> AgentState:
    """Evaluate whether the current window has enough evidence to answer the query."""
    
    prompt = f"""
    You are an expert AI retrieval judge. Your task is to evaluate whether the context window contains enough relevant evidence to answer the user's query.
    
    Relevance definition: The context directly supports a useful, grounded answer to the query.

    User Query: {state["query"]}
    Context Window: {state["current_window"]}

    Scoring Rubric:
    5 - Fully relevant and enough to answer.
    4 - Mostly relevant and likely enough.
    3 - Partially relevant, but may need more context.
    2 - Weakly relevant.
    1 - Not relevant.
    
    If the score is 4 or 5, exactly return 'enough'.
    If the score is 1, 2, or 3, exactly return 'need_more'.
    """  
    decision = llm_model.invoke([HumanMessage(content=prompt)]).content.lower()
    enough = "enough" in decision and "need_more" not in decision
    
    return {"enough": enough}

def load_next_window(state:AgentState) -> AgentState:
    """slide the current window slider to the next if the info is not relevent"""
    
    next_cursor = state["cursor"] + 1
    all_window = state["all_window"]
    
    if next_cursor < len(all_window):
        return {
            "cursor": next_cursor,
            "current_window": all_window[next_cursor]
        }
    return {"current_window": ""}

def decide_next_step(state:AgentState) -> AgentState:
    """decide if need more context/window, then slide window"""
    
    current_cursor = state.get("cursor", 0)
    all_w = state.get("all_window", [])

    if state.get("enough"):
        return "FINISHED"

    if current_cursor < len(all_w) - 1:
        return "NEXT_WINDOW"

    return "FINISHED"
    # state["cursor"] += 1
    
    # if (state["current_window"] == "") or (state["doc_id"] == "") : state["use_web"] = True ; return "WEB_SEARCH"

    # elif (state["cursor"] < len(state["all_window"])): 
    #     state["use_web"] = False
    #     state["current_window"] = state["all_window"][state["cursor"]]

    #     return "RAG_SEARCH"
    
    # else: state["use_web"] = True ;  return "WEB_SEARCH"

def route_query(state: AgentState) -> str:
    """Route which path to take according to the user's query, rag or web or direct llm response"""

    doc_id = state.get("doc_id")
    query = state["query"].lower()
    web_triggers = [
        "current",
        "latest",
        "recent",
        "today",
        "news",
        "breaking",
        "live",
        "now",
        "this week",
        "this month",
        "updates",
        "update",
    ]

    if any(trigger in query for trigger in web_triggers):
        return "WEB_SEARCH"

    direct_triggers = {
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "ok",
        "okay",
        "bye",
    }
    normalized_query = query.strip(" !?.")
    if normalized_query in direct_triggers:
        return "LLM_RESPONSE"

    if doc_id:
        return "RAG_SEARCH"

    prompt = f"""
    You are a routing classifier. Return only one label: DIRECT or RAG_SEARCH or WEB_SEARCH after checking :

    DIRECT - greeting, random chat, general message, or no retrieval needed
    RAG_SEARCH - user is asking about "from the doc" or "from the provided file", if the uploaded document and doc_id exists
    WEB_SEARCH - user needs latest/current/external web information

    doc_id: {doc_id or "none"}
    user_message: {state["query"]}

    Label:
    """
    decision = llm_model.invoke([HumanMessage(content=prompt)]).content.strip().upper()

    if "RAG_SEARCH" in decision and doc_id:
        return "RAG_SEARCH"

    if "WEB_SEARCH" in decision:
        return "WEB_SEARCH"

    return "LLM_RESPONSE"

def decide_initial_routing(state: AgentState) -> str:
    """Decides where to go immediately after START"""
    # If no doc_id exists, skip RAG completely and fetch from Web

    if not state.get("doc_id"):
        return "WEB_SEARCH"
    return "RAG_SEARCH"

def finalize_answer(state:AgentState) -> AgentState:
    """Retrieves the final answer from big llm"""

    prompt = (
            f"from the user query : {state['query']}\n"
            f"retireve answer from the context : {state['current_window']} \n"
            f"please give a comprihensive well structured response for the user"
            f"Answer only using the context"
            f"if the context does not contain the answer, say you could not find it from the uploaded document."
              )
    
    response = llm_model.invoke([HumanMessage(content=prompt)]).content
   
    return {"final_answer" : response}

def graph(state:AgentState) -> AgentState:
    """jsut for fun"""
    pass

agentGraph = StateGraph(AgentState)

# create nodes..
agentGraph.add_node("llm_direct", direct_answer)
agentGraph.add_node("rag_system",prepare_rag_windows)
agentGraph.add_node("web_system", web_search)
agentGraph.add_node("next_window", load_next_window)
agentGraph.add_node("final_llm_answer", finalize_answer)
agentGraph.add_node("clarity_check", reason_over_window)

# create edges..
agentGraph.add_conditional_edges(
    START,
    route_query,
    {
        "RAG_SEARCH" : "rag_system",
        "WEB_SEARCH" : "web_system",
        "LLM_RESPONSE" : "llm_direct", # to be added in the decide_initial_routing
    }
)

# agentGraph.add_edge("rag_system", "next_window")
agentGraph.add_edge("rag_system", "clarity_check")
agentGraph.add_edge("web_system", "clarity_check")
agentGraph.add_edge("next_window", "clarity_check")
agentGraph.add_edge("llm_direct", END)

agentGraph.add_conditional_edges(
    "clarity_check",
    decide_next_step,
    {
        "NEXT_WINDOW" : "next_window",
        "FINISHED" : "final_llm_answer",
    }
)

agentGraph.add_edge("final_llm_answer", END)

app = agentGraph.compile()

def _initial_state(query: str, doc_id: str | None = None, session_summary: str | None = None) -> AgentState:
    return {
        "messages": [],
        "query": query,
        "doc_id": doc_id,
        "chunk_ids": [],
        "cursor": 0,
        "window": 4150,
        "slide_window": int(4150 * 0.15),
        "context": "",
        "current_window": "",
        "all_window": [],
        "running_summary": "",
        "final_answer": "",
        "enough": False,
        "use_web": False,
        "source": "",
        "rest": 0,
        "session_summary": session_summary or "No conversation yet.",
    }

async def async_final_answer(
    query: str,
    doc_id: str | None = None,
    session_summary: str | None = None
) -> str:
    """Async graph entrypoint for FastAPI or other async callers."""
    result = await app.ainvoke(_initial_state(query, doc_id, session_summary))
    return result.get("final_answer", "")

def final_answer(query:str, doc_id:str |None=None, session_summary: str | None = None):
    """Finally gives the final response from the big llm generated"""
    return asyncio.run(async_final_answer(query, doc_id, session_summary))

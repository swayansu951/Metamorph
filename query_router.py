import ollama
from tool_registry import TOOLS
from simple_rag.main import GENERATE
from langchain_core.tools import tool
from typing import TypedDict, Optional
from langchain_ollama import ChatOllama
from tool.rag_tool import make_rag_tool
from tool.webscraping import run_pipeline
from langgraph_bigtool import create_agent
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph,END,START
from langgraph.store.memory import InMemoryStore
from typing import TypedDict, Annotated , Sequence
from simple_rag.database.embedder import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import trim_messages, BaseMessage, SystemMessage, HumanMessage


class AgentState(TypedDict):
    messages : Annotated[Sequence[BaseMessage], add_messages]

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
                        keep_alive="1m",
                        num_thread=6,
                        temperature=0.1,
                        )

# conversational memmory access..
store = InMemoryStore()
namespace = ("tools", "agent_tools")

tools = TOOLS()

# urls for web crwaling
URLS = {
    "finance" : ["https://yahoo.com",
                    "https://sec.gov"],
    "health" : ["https://cdc.gov",
                "https://who.int"],
    "science":["https://arxiv.org",
                "https://nasa.gov"],
    "geography":["https://usgs.gov",
                "https://worldbank.org"],
    "legals":["https://indiacode.nic.in",
                "https://govinfo.gov"]
}
# extra registry..
def build_registry(doc_id: str | None):
    
    registry = {
            "web_search": run_pipeline,
    }
    
    if doc_id:
        registry["rag_search"] = make_rag_tool(doc_id)

    return registry

# sliding window concept...
message_trimmer = trim_messages(max_tokens = 4000,
                                include_system = True,
                                token_counter = llm_model,
                                allow_partial = False,
                                start_on = "human",
                                strategy="last"
                                )

# implemented the sliding window over the chat_history..
def run_query(query:str, doc:str|None=None, chat_history = None):
    """LLm's response structure with implemented sliding window"""
    
    registry = build_registry(doc)

    agent_graph = create_agent(
        llm=llm_model,
        tool_registry=registry
    )
    raw_message = [system_prompt,
                   *(chat_history or []),
                   HumanMessage(query)
                   ]
    trimed_message = message_trimmer.invoke(raw_message)
    app = agent_graph.compile()

    return app.invoke(
        {
        "messages" : trimed_message
        }
    )

user_prompts = [msg["content"] for msg in messages if msg["role"] == "user"]# only contains the system prompt. So the graph is immediately streamed with an empty user query.

window = 4500
slide_window = 2000

# preserve the context window and accuracy increase LangGraph
class AgentState2(TypedDict):
    query : str
    doc_id : Optional[str]
    chunk_ids : list[int]
    cursor : int 
    context : str
    current_window : str
    all_window : list[str]
    running_summary : str
    final_answer : str
    enough : bool
    use_web : bool
    rest : int

def prepare_rag_windows(state:AgentState2) -> AgentState2:
    """"prepares the chunk window and the window split from the retireved context.
        1. Set the window size, e.g. 4000 from the original context retrieved.
        2. Slider window to be 10 - 15 % of the window size.
        3. set the cursor original pointer at 0.
        4. Set the current window be the slider window which feed the context to the LLM.
    """
    state["context"] = generator.generate(user_input=state["query"], doc_id=state["doc_id"])
    window = state.get("window", 4000)
    slider_window = state.get("slide_window", int(window * 0.15))

    spliter = RecursiveCharacterTextSplitter(
                                    chunk_size = window,
                                    chunk_overlap = slider_window,
                                    separators=["\n\n","\n"," ",""],
                                )
    windows = spliter.split_text(state["context"])
    
    state["window"] = window
    state["slide_window"] = slider_window
    state["cursor"] = 0
    state["all_window"] = windows
    state["current_window"] = windows[0] if windows else ""
    state["rest"] = state["window"] - state["slide_window"]
    
    return state

def load_next_window(state:AgentState2) -> AgentState2:
    """slide the current window slider to the next if the info is not relevent"""
    
    state["cursor"] += 1
    state["current_window"] = state["all_window"][state["cursor"]]
    return state

def reason_over_window(state:AgentState2) -> AgentState2:
    """llm on that window to decide which path to take, RAG_SEARCH or WEB_SEARCH"""
    pass

def decide_next_step(state:AgentState2) -> AgentState2:
    """decide if need more context/window, then slide window"""
    
    state["cursor"] += 1
    if len(state["running_summary"]) < 0: state["use_web"] = True ; return "WEB_SEARCH"
    
    elif (state["current_window"] == ""): state["use_web"] = True ; return "WEB_SEARCH"

    elif (state["cursor"] < len(state["all_window"])): 
        state["use_web"] = False
        state["current_window"] = state["all_window"][state["cursor"]]

        return "RAG_SEARCH"
    
    else: state["use_web"] = True ;  return "WEB_SEARCH"

def web_search(state:AgentState2) -> AgentState2:
    """call web_search tool for retireve information from web if no document or less precise info in document"""
    state["context"] = run_pipeline(state["query"], url=[URLS["finance"],
                                                         URLS["geography"],
                                                         URLS["health"],
                                                         URLS["legals"],
                                                         URLS["science"]
                                                         ]
                                    )
    window = state.get("window", 4000)
    slider_window = state.get("slide_window", int(window * 0.15))

    spliter = RecursiveCharacterTextSplitter(
                                    chunk_size = window,
                                    chunk_overlap = slider_window,
                                    separators=["\n\n","\n"," ",""],
                                )
    windows = spliter.split_text(state["context"])

    state["window"] = window
    state["slide_window"] = slider_window
    state["cursor"] = 0
    state["all_window"] = windows
    state["current_window"] = windows[0] if windows else ""
    state["rest"] = state["window"] - state["slide_window"]

    return state

def finalize_answer(state:AgentState2) -> AgentState2:
    """Retrieves the final answer"""
    if "WEB_SEARCH":
        state["final_answer"] += state["all_window"]

    else :
        state["final_answer"] += state["current_window"]
    
    return state

def graph(state:AgentState) -> AgentState:
    """jsut for fun"""
    pass
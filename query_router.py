import ollama
from typing import TypedDict, Optional
from tool_registry import TOOLS
from langchain_core.tools import tool
from tool.rag_tool import make_rag_tool
from simple_rag.database.embedder import embed_model
from langchain_ollama import ChatOllama
from simple_rag.main import GENERATE
from langgraph.graph import StateGraph,END,START
from tool.webscraping import run_pipeline
from langgraph_bigtool import create_agent
from langgraph.graph.message import add_messages
from langgraph.store.memory import InMemoryStore
from typing import TypedDict, Annotated , Sequence
from langchain_core.messages import trim_messages, BaseMessage, SystemMessage, HumanMessage


class AgentState(TypedDict):
    
    messages = Annotated[Sequence[BaseMessage], add_messages]

# Simple RAG response generator
generator = GENERATE()

# widely used system prompt..
system_prompt = SystemMessage("Answer the question using the context below. If the answer is not found in the context or not relevant or no document uploaded, then use web crawling to get answer'")

# base message schema/structure..
messages = [{'role' : 'system' , 'content' : system_prompt}]

# Single unit controling model..
llm_model = ChatOllama(model='llama3.1:8b-instruct-q5_K_S', 
                        stream=True, 
                        keep_alive="1m"
                        )

# conversational memmory access..
store = InMemoryStore()
namespace = ("tools", "agent_tools")

tools = TOOLS()

# extra registry..
def build_registry(doc_id: str | None):
    
    registry = {
            "web_search": run_pipeline,
    }
    
    if doc_id:
        registry["rag_search"] = make_rag_tool(doc_id)

    return registry
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# for tool_id, tool in tools.registry.items():
#     tool_metadata = f"tool id : {tool_id}, tool name: {tool.__name__}, tool description: {tool.__doc__}"
#     vector_embed = embed_model.encode(tool_metadata)

#     store.put(
#         namespace=namespace,
#         key=tool_id,
#         item={"name" : tool_id, "description" : tool.__doc__},
#         index={"embedding" : vector_embed}
#     )
# ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# sliding window concept...
message_trimmer = trim_messages(max_tokens = 3890,
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
        "message" : trimed_message
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
    current_window : str
    running_summary : str
    final_answer : str
    enough : bool
    use_web : bool

def prepare_rag_windows(state:AgentState2) -> AgentState2:
    """"prepares the chunk window from the retireved documnet """
    

def load_next_window(state:AgentState2) -> AgentState2:
    """pick the current rag window"""
    pass

def reason_over_window(state:AgentState2) -> AgentState2:
    """llm on that window"""
    pass

def decide_next_step(state:AgentState2) -> AgentState2:
    """decide if need more context/window, then slide window"""
    pass

def web_search(state:AgentState2) -> AgentState2:
    """call web_search tool for retireve information from web if no document or less precise info in documnet"""
    pass

def finalize_answer(state:AgentState2) -> AgentState2:
    """Retrieves the final answer"""
    pass

def graph(state:AgentState) -> AgentState:
    """jsut for fun"""
    pass
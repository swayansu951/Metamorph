import json
import re
from typing import TypedDict
from contextlib import contextmanager # to be used in future update
from .uuid_registry import REGISTRY
from langchain_core.messages import HumanMessage
from langchain_ollama.chat_models import ChatOllama

model = "llama3.2:3b"

class QueryState(TypedDict):
    """data type should be based on this to prevent any error\n
        query : str\n
        output : list[str]\n
        agent_id : str\n
    """
    query : str
    output : dict[str]
    agent_id : str

class filter:

    PROMPT = ("""
        You are a query classification agent.
        Return ONLY valid JSON. Do not include markdown, code fences, variable names,
        comments, explanations, or text before/after the JSON.

        Required JSON shape:
        {
            "query": "the original user query",
            "query_type": "text_only | image_needed | video_needed | mixed | link_only",
            "domain": "programming | science | legal | medical | news | finance | research | general",
            "freshness": "latest | recent | historical",
            "source_quality": "official | academic | trusted_news | docs | general",
            "media_need": "none | optional | required",
            "search_depth": "quick | medium | deep"
        }
        """)

    def _parse_json_response(self, content: str) -> dict:
        """Parse strict JSON, with fallback for common LLM wrappers."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        cleaned = re.sub(r"^\s*\w+\s*=\s*", "", cleaned)

        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise json.JSONDecodeError("No JSON object found", content, 0)

        return json.loads(match.group(0))
    
    def query_filer(self, state : QueryState) -> QueryState:
        """Filters the query according to the given prompt\n
            return a structure contains :\n
            query : str\n
            output : dict[str]\n
            agent_id : str\n
            The main is output contains the LLM response in the json structure else the error message\n
        """
        agent_name = "filter_agent"
        id = REGISTRY.get_or_create_agent(agent_name)
        REGISTRY .task_counts(agent_name)
        data = ChatOllama(
            model=model,
            stream=False,
            num_gpu = -1,
            temperature = 0.1,
            keep_alive=6,
        )
        response = data.invoke(self.PROMPT + "\n\n" + state['query'])
        try:
            output = self._parse_json_response(response.content)
        except json.JSONDecodeError as e:
            output = {"error" : "failed to parse LLM Response",
                      "exception" : str(e),
                       "raw context" : response.content
                       }

        output.setdefault("query", state["query"])
        output.setdefault("query_type", "text_only")
        output.setdefault("domain", "general")
        output.setdefault("freshness", "recent")
        output.setdefault("source_quality", "general")
        output.setdefault("media_need", "none")
        output.setdefault("search_depth", "quick")
        
        state['output'] = output
        state['agent_id'] = id

        return state

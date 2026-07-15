# checks if the provided query don't violet app's policy to avoid unothorized access
"""A asyncronious function that validates and refines the user's query for proper llm forward feed \n use this as Exampl :: >>> await variable(Query_Update)"""
import re
from langchain_ollama import ChatOllama
from ModelnPrompt import SYSTEM_PRMOPTS, MODELS
from langchain.messages import SystemMessage, HumanMessage

class Validator:
    async def validate_query(self, query:str)-> str:
        patterns = [
        r'(?i)\bignore\s+(all\s+)?previous\s+instructions\b',
        r'(?i)\bdisregard\s+(the\s+)?(prior\s+)?instructions?\b',
        r'(?i)\breveal\s+(your\s+)?(system|base)\s+prompt\b',
        r'(?i)\bprint\s+(system\s+)?instructions?\b',
        r'(?i)\bact\s+as\s+a\s+(developer|admin|security)\s+.*'
        ]
        
        sanitized = query
        for pattern in patterns:
            # Replace malicious patterns with a neutral token
            sanitized = re.sub(pattern, "[FILTERED]", sanitized)
            
        return sanitized.strip()

    async def Query_Update(self, query:str) -> str:
        """Return a sanitized and re-written query for downstream model calls."""

        sanitized_query = await self.validate_query(query)
        Prompt = [SystemMessage(content=SYSTEM_PRMOPTS.validator),
                  HumanMessage(content=sanitized_query)]
        
        model = ChatOllama(model=MODELS.query_router,
                         stream=False,
                         num_gpu=-1,
                         keep_alive=0,
                         temperature=0.2,
                         )

        validated_query = model.invoke(Prompt)
        
        return validated_query
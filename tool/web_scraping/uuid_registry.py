"""use by calling default REGISTRY\n
ID_REGISTRY\n
uuidInfo:\n
    uuid\n
    created\n
    last_used\n
    task_count\n
    """
import json
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from dataclasses import dataclass
from typing import TypedDict, Dict, Optional

@dataclass
class uuidInfo():
    uuid : str
    created : datetime
    last_used : datetime
    task_count : int = 0

class ID_REGISTRY():
    """
        Contains all the registry of uuids and agents.
        functions:\n
        get_or_create_agent : agent_name ( checks whether the agent is present or not if not then create a new registry for that else use the uuid stored )\n
        task_count : whenever the agent is called the task count will increment by 1, helps in logs how many time does the agent has been used.\n
    """

    def __init__(self, path = "uuid_registry"):
        
        self.path = Path(path)
        self.id_registry = self.path / "uuid_registry.json" # store every registry in this file..
        self.path.mkdir(parents=True, exist_ok=True)
        self._agent : Dict[str, uuidInfo] = {} # make the structure of the log

    def save_details(self):
        with open(self.id_registry, "w", encoding="utf-8") as f:
            json.dump(self._agent, f, ensure_ascii= False, indent=4)   

    def get_or_create_agent(self, agent_name : str) -> str:
        """use the pre-registered data or else creates a new agent with new uuid
        contains a dict structure :\n
            uuid : str\n
            created : datetime\n
            last_used : datetime\n
            task_count : int = 0\n
        return the agent uuid only
        """
        if agent_name in self._agent: # carry the preregistred one 
            self._agent[agent_name].last_used = datetime.now()
            return self._agent[agent_name].uuid
        
        else : # create a new registry if not present
            agent_uuid = str(uuid4())
            self._agent[agent_name] = uuidInfo(
                uuid = agent_uuid,
                created = datetime.now(),
                last_used=datetime.now(),
           ) 

        return agent_uuid

    def task_counts(self, agent_nama: str) -> None:
        """if the agent is called to perform a task simply increment the task count,\f
        only for log file, nothing to return"""
        if agent_nama in self._agent : self._agent[agent_nama].task_count += 1

    def get_info(self, agent_name : str) -> Optional[uuidInfo]:
        """return only the agent's info based on the agent name"""
        return self._agent.get(agent_name)
    
    def delete_agent(self, agent_name : str) ->bool:
        """to delete a agent from the registry if not needed anymore"""
        if agent_name in self._agent: 
            self._agent.pop(agent_name, None)
            self.save_details()

            return True
        return False
REGISTRY = ID_REGISTRY()
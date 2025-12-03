from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END


class ImpactMappingAgent(TypedDict):
    entities: List[str]


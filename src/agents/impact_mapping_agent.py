from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END
from src.core import (
    fetch_entities, create_story_impacts_table, insert_story_impacts
)
from src.utils import (
    load_mappings
)


class ImpactMappingAgent(TypedDict):
    entities: List[str]


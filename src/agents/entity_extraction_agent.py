from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END
from src.core import (
    fetch_unique_stories, create_news_entities_table, insert_entities
)
from src.utils import (
    load_local_or_download, match_rules, postprocess_entities
)



from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END
from src.core import (
    fetch_unprocessed_entities, create_story_impacts_table, insert_story_impacts
)
from src.utils import (
    load_mapping, compute_impacts_for_entities
)
import os, json


class ImpactMappingAgent(TypedDict):
    entities: List[Dict]
    computed_impacts: List[Dict]
    saved_count: int


def load_entities(state: ImpactMappingAgent) -> ImpactMappingAgent:
    """Fetch entity rows to be impact-mapped"""
    items = state["entities"]
    if items == []:
        create_story_impacts_table()
        items = fetch_unprocessed_entities()
        
    state["entities"] = items
    print(f"[Impact Mapping Agent] Loaded {len(items)} stories for impact mapping.")
    return state

def compute_impacts(state: ImpactMappingAgent) -> ImpactMappingAgent:
    """Compute impact mapping for each story using mapping rules"""
    company_map, symbol_map, regulator_rules, policy_rules, sector_map = load_mapping()
    computed = []

    for row in state["entities"]:
        story_id = row["story_id"]
        entities = row["entities"]

        impacts, summary = compute_impacts_for_entities(
            entities=entities,
            company_to_symbol=company_map,
            symbol_to_sector=symbol_map,
            regulator_rules=regulator_rules,
            policy_rules=policy_rules,
            sector_to_symbols=sector_map,
        )

        computed.append({
            "story_id": story_id,
            "impacted_assets": impacts,
            "summary": summary,
        })
    
    state["computed_impacts"] = computed
    print(f"[Impact Mapping Agent] Computed Impacts for {len(computed)} stories.")
    return state

def save_results(state: ImpactMappingAgent) -> ImpactMappingAgent:
    """Save impact results into the db."""
    create_story_impacts_table()
    saved = 0

    for item in state["computed_impacts"]:
        try:
            insert_story_impacts(
                story_id=item["story_id"],
                impacts=item["impacted_assets"],
                summary=item["summary"]
            )
            saved += 1
        except Exception as e:
            print(f"[Impact Mapping Agent] Failed to save story.")

    state["saved_count"] = saved
    print(f"[Impact Mapping Agent] Saved {saved} results to the DB")
    return state


def build_impact_mapping_graph():
    graph = StateGraph(ImpactMappingAgent)

    graph.add_node("load_entities", load_entities)
    graph.add_node("compute_impacts", compute_impacts)
    graph.add_node("save_results", save_results)

    graph.set_entry_point("load_entities")
    graph.add_edge("load_entities", "compute_impacts")
    graph.add_edge("compute_impacts", "save_results")
    graph.add_edge("save_results", END)

    return graph.compile()


if __name__ == "__main__":
    # run on CLI using "python -m src.agents.impact_mapping_agent"
    impact_app = build_impact_mapping_graph()

    result = impact_app.invoke({
        "pending_entities": [],
        "computed_impacts": [],
        "saved_count": 0
    })
    
    img_bytes = impact_app.get_graph().draw_mermaid_png()
    os.makedirs("graph_images", exist_ok=True)
    outpath = "graph_images/impact_mapping_graph.png"
    with open(outpath, "wb") as f:
        f.write(img_bytes)

    print(f"Graph saved to {outpath}")
# src/search/rag.py
from typing import List, Dict
from src.search.retriever import Retriever

class RAG:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever

    def retrieve_context(self, structured_query: Dict, top_k:int = 5) -> Dict:
        # map assets
        mapping = self.retriever.map_query_to_assets(structured_query)
        rewritten = structured_query.get("rewritten")

        # Use both rewritten query and expanded asset list to form the search query
        asset_phrase = ""
        if mapping["symbols"]:
            asset_phrase = " ".join(mapping["symbols"])
        elif mapping["sectors"]:
            asset_phrase = " ".join(mapping["sectors"])

        search_text = rewritten
        if asset_phrase:
            search_text = f"{rewritten} {asset_phrase}"

        hits = self.retriever.semantic_search(search_text, top_k=top_k)

        # build context text
        context_items = []
        for h in hits:
            snippet = h.get("article_title") or ""
            snippet += "\n" + (h.get("combined_text") or "")[:1000]  # cap snippet
            context_items.append({"id": h["id"], "title": h.get("article_title"), "snippet": snippet, "score": h.get("score")})

        return {
            "mapping": mapping,
            "hits": context_items,
            "rewritten": rewritten
        }

# src/search/retriever.py
import json
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from src.search.embedding_index import EmbeddingIndex
from src.core.database import (
    fetch_stories_by_sector,
    fetch_stories_by_ids,
    fetch_all_unique_stories
)
from src.utils.impact_mapping import load_mapping

company_to_symbol, symbol_to_sector, regulator_rules, policy_rules, sector_to_symbols = load_mapping()

class Retriever:
    def __init__(self, model_name=None):
        self.idx = EmbeddingIndex()
        try:
            self.idx.load()
        except Exception:
            self.idx = None

    def ensure_index(self, stories):
        self.idx = EmbeddingIndex()
        self.idx.build_from_stories(stories)
        self.idx.save()

    # 1) query_type -> company/sector mapping
    def map_query_to_assets(self, structured_query: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Accepts structured_query with keys: rewritten, query_type, entities
        Returns dict: {"companies": [...], "sectors": [...], "symbols": [...]}
        """
        qtype = structured_query.get("query_type", "unknown")
        ents = structured_query.get("entities", []) or []
        companies = []
        sectors = []
        symbols = []

        if qtype == "company":
            # entities assumed company names — fuzzy-match via mappings
            for e in ents:
                sym = company_to_symbol.get(e) or company_to_symbol.get(e.lower())
                if sym:
                    symbols.append(sym)
                    companies.append(e)
        elif qtype == "sector":
            for e in ents:
                sectors.append(e)
                # sector->symbols mapping stored with lowercase keys
                syms = sector_to_symbols.get(e.lower(), [])
                symbols.extend(syms)
        elif qtype in ("regulator", "policy"):
            # use regulator_rules/policy_rules to get sectors, then symbols
            for e in ents:
                rule = regulator_rules.get(e.lower()) or policy_rules.get(e.lower())
                if rule:
                    for sec in (rule.get("sectors") or []):
                        syms = sector_to_symbols.get(sec.lower(), [])
                        symbols.extend(syms)
                        sectors.append(sec)
        else:
            for e in ents:
                if e.lower() in sector_to_symbols:
                    sectors.append(e)
                    symbols.extend(sector_to_symbols.get(e.lower(), []))
                else:
                    sym = company_to_symbol.get(e) or company_to_symbol.get(e.lower())
                    if sym:
                        symbols.append(sym)
                        companies.append(e)

        # dedupe
        symbols = list(dict.fromkeys(symbols))
        companies = list(dict.fromkeys(companies))
        sectors = list(dict.fromkeys(sectors))

        return {"companies": companies, "sectors": sectors, "symbols": symbols}

    # 2) sector -> all related news
    def stories_for_sector(self, sector_name: str, limit: Optional[int]=100) -> List[Dict]:
        return fetch_stories_by_sector(sector_name, limit=limit)

    # 3) regulator -> filtered news
    def stories_for_regulator(self, regulator_name: str, limit: int = 100) -> List[Dict]:
        reg_key = regulator_name.lower()
        rule = regulator_rules.get(reg_key)
        if not rule:
            return []

        sectors = rule.get("sectors", [])
        combined = []

        for sec in sectors:
            rows = fetch_stories_by_sector(sec, limit=limit)
            combined.extend(rows)

        # dedupe by id
        seen = set()
        out = []
        for r in combined:
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append(r)
        return out


    # semantic retrieval using embeddings: returns stories with scores
    def semantic_search(self, query_text: str, top_k: int = 10) -> List[Dict]:
        if self.idx is None:
            raise RuntimeError("Embedding index not built. Call ensure_index(...) first.")

        hits = self.idx.query(query_text, top_k=top_k)
        ids = [h["id"] for h in hits]

        rows = fetch_stories_by_ids(ids)

        # attach scores
        id_to_score = {h["id"]: h["score"] for h in hits}
        out = [{**r, "score": id_to_score.get(r["id"], 0.0)} for r in rows]

        # sort by score
        return sorted(out, key=lambda x: -x["score"])
    

    def get_relevant_news(self, structured, mapped, top_k=15):
        results = []

        # 1) If sector found → get all stories for that sector
        for sec in mapped["sectors"]:
            results.extend(self.stories_for_sector(sec))

        # 2) If specific symbols found → fetch related stories
        for sym in mapped["symbols"]:
            stories = self.stories_for_company_symbol(sym)
            results.extend(stories)

        # 3) If regulator query → fetch related sectors
        if structured["query_type"] == "regulator":
            for ent in structured["entities"]:
                results.extend(self.stories_for_regulator(ent))

        # 4) Fallback → semantic search
        semantic_hits = self.semantic_search(structured["rewritten"], top_k=top_k)
        results.extend(semantic_hits)

        # Deduplicate by story ID
        seen = set()
        merged = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                merged.append(r)

        return merged



if __name__ == "__main__":
    r = Retriever()

    sq = {"query_type": "sector", "entities": ["banking"]}
    print(r.map_query_to_assets(sq))

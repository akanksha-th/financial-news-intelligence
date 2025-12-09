# src/search/retriever.py
import json
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from ...core.embedding_index import EmbeddingIndex
from src.core.database import (
    fetch_stories_by_sector,
    fetch_stories_by_ids,
    fetch_all_unique_comp_stories
)
from src.utils.impact_mapping import load_mapping

company_to_symbol, symbol_to_sector, regulator_rules, policy_rules, sector_to_symbols, symbol_to_company = load_mapping()

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
        ents_raw = structured_query.get("entities", {}) or {}
        companies = []
        sectors = []
        symbols = []

        if isinstance(ents_raw, dict):
            ents = []
            for v in ents_raw.values():
                if isinstance(v, list):
                    ents.extend(v)
                elif isinstance(v, str):
                    ents.append(v)
        else:
            ents = ents_raw or []

        ents = [e.lower().strip() for e in ents]

        # Build fuzzy lookup
        company_fuzzy = {}
        for full_name, symbol in company_to_symbol.items():
            key = full_name.lower().strip()
            company_fuzzy[key] = symbol
            
            # Also support versions without "limited", "ltd"
            short = key.replace("limited", "").replace("ltd", "").strip()
            company_fuzzy[short] = symbol
            
            tokens = short.split()
            company_fuzzy[" ".join(tokens[:2])] = symbol


        if qtype == "company":
            # entities assumed company names — fuzzy-match via mappings
            for e in ents:
                sym = company_fuzzy.get(e.lower())

                if sym:
                    symbols.append(sym)
                    companies.append(e)
                    sect = symbol_to_sector[sym]["sector"]
                    sectors.append(sect)
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
    
    def stories_for_company_symbol(self, company_symbol: str):
        comp = symbol_to_company.get(company_symbol)
        if not comp:
            return []

        # strip "Limited", "Ltd", "Pvt." etc
        # comp_norm = (
        #     comp.replace("Limited", "")
        #         .replace("Ltd", "")
        #         .replace("Pvt", "")
        #         .replace(".", "")
        #         .strip()
        #         .lower()
        # )
        rows = fetch_all_unique_comp_stories(company_like=comp)

        return rows


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
    

    def get_relevant_news(self, structured, mapped, top_k=7, use_semantic=True):
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
        semantic_hits = []
        semantic_score_map = {}
        if use_semantic:
            semantic_hits = self.semantic_search(structured["rewritten"], top_k=top_k)
            semantic_score_map = {item["id"]: item["score"] for item in semantic_hits}
            results.extend(semantic_hits)

        # Deduplicate by story ID
        seen = {}
        for r in results:
            rid = r["id"]
            if rid not in seen:
                seen[rid] = r.copy()

            if rid in semantic_score_map:
                seen[rid]["score"] = semantic_score_map[rid]

            if "score" not in seen[rid]:
                seen[rid]["score"] = None

        final = sorted(seen.values(), key=lambda x: (x["score"] is not None, x["score"]), reverse=True)
        return final



if __name__ == "__main__":
    # run on CLI using "python -m src.query_system.search.retriever"
    r = Retriever()

    sq = {'rewritten': "What is the latest news on HDFC bank's performance in terms of future prospects?", 
            'query_type': 'company', 
            'entities': {'companies': ['hdfc bank']},
            'time_horizon': 'short'}
    assets = r.map_query_to_assets(sq)
    print(r.get_relevant_news(sq, assets, use_semantic = r.idx is not None))

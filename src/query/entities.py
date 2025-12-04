import re, json
from pathlib import Path
from typing import Dict, List

ASSETS_DIR = Path("assets")
FIN_GAZ_PATH = ASSETS_DIR / "fin_gazetteers.json"

try:
    with open(FIN_GAZ_PATH, "r", encoding="utf-8") as fh:
        _GAZ = json.load(fh)
except Exception:
    _GAZ = {}

def _load_list(key):
    v = _GAZ.get(key)
    if v is None:
        return []
    if isinstance(v, dict):
        return list(v.keys())
    if isinstance(v, list):
        return v
    return [str(v)]

_G_REGULATORS = [x for x in _load_list("regulators")]
_G_INDICES = [x for x in _load_list("indices")]
_G_SECTORS = [x for x in _load_list("sectors")]
_G_COMPANIES_CUSTOM = [x for x in _load_list("companies_custom")]
_G_POLICIES = _load_list("policies") or _load_list("policy_terms") or []
_G_KPIS = _load_list("kpi_terms") or []
_G_FIN_TERMS = _load_list("financial_terms") or []

def simple_rule_extract(query: str) -> Dict[str, List[str]]:
    q = query.lower()
    out = {"companies": [], "sectors": [], "regulators": [], "policies": [], "indices": [], "kpis": [], "financial_terms": []}

    # companies
    for cname in _G_COMPANIES_CUSTOM:
        if cname.lower() in q and cname not in out["companies"]:
            out["companies"].append(cname)

    # sectors
    for s in _G_SECTORS:
        if s.lower() in q and s not in out["sectors"]:
            out["sectors"].append(s)

    # regulators
    for r in _G_REGULATORS:
        if r.lower() in q and r not in out["regulators"]:
            out["regulators"].append(r)

    # policies
    for p in _G_POLICIES:
        if p.lower() in q and p not in out["policies"]:
            out["policies"].append(p)

    # indices
    for idx in _G_INDICES:
        if idx.lower() in q and idx not in out["indices"]:
            out["indices"].append(idx)

    # KPIs and financial terms (regex / substring)
    for k in _G_KPIS:
        if k.lower() in q and k not in out["kpis"]:
            out["kpis"].append(k)
    for ft in _G_FIN_TERMS:
        if ft.lower() in q and ft not in out["financial_terms"]:
            out["financial_terms"].append(ft)

    # percentages
    percents = re.findall(r"\b\d+(\.\d+)?\s?%|\b\d+\s?bps\b", query, flags=re.I)
    if percents:
        out.setdefault("financial_terms", [])
        for p in set(re.findall(r"\d+(\.\d+)?%|\d+\s?bps", query, flags=re.I)):
            out["financial_terms"].append(p)

    # de-duplicate
    for k in out:
        seen = []
        for v in out[k]:
            if isinstance(v, str) and v not in seen:
                seen.append(v)
        out[k] = seen

    return out

def extract_entities_from_query(query: str) -> Dict[str, List[str]]:
    return simple_rule_extract(query)

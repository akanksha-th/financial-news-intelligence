import os, json
from collections import defaultdict
from typing import Dict, List, Any
from pathlib import Path

try:
    from rapidfuzz import process, fuzz
    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False

ASSETS_DIR = Path("assets")
COMPANY_TO_SYMBOL_PATH = os.path.join(ASSETS_DIR, "company_to_symbol.json")
SYMBOL_TO_SECTOR_PATH = os.path.join(ASSETS_DIR, "symbol_to_sector.json")
SECTOR_TO_SYMBOLS_PATH = os.path.join(ASSETS_DIR, "sector_to_symbols.json")
REGULATOR_RULES_PATH = os.path.join(ASSETS_DIR, "regulator_impact_rules.json")
POLICY_RULES_PATH = os.path.join(ASSETS_DIR, "policy_impact_rules.json")
# print("All paths are correct!")

SCORES = {
    "direct": 1.00,
    "gazetteer": 0.95,
    "sector": 0.70,
    "regulatory": 0.60,
    "policy": 0.60,
    "index": 0.50,
    "semantic": 0.40,
}

PRIORITY_ORDER = ["direct", "gazetteer", "sector", "regulatory", "policy", "index", "semantic"]

def load_safe_json(path: str) -> Dict:
    if not os.path.exists(path):
        print(f"[Impact Mapping] !!!Mapping file not found!!!")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def load_mapping():
    """Loads All json mappings"""
    company_to_symbol = load_safe_json(COMPANY_TO_SYMBOL_PATH)
    symbol_to_sector = load_safe_json(SYMBOL_TO_SECTOR_PATH)
    regulator_rules = load_safe_json(REGULATOR_RULES_PATH)
    policy_rules = load_safe_json(POLICY_RULES_PATH)
    sector_to_symbols = load_safe_json(SECTOR_TO_SYMBOLS_PATH)

    return company_to_symbol, symbol_to_sector, regulator_rules, policy_rules, sector_to_symbols

def normalize_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(name.strip().split()).lower()

def fuzzy_match_company(name: str, company_to_symbol: Dict[str, str], top_k: int = 3, score_threshold: int = 80):
    if not name:
        return None

    name_norm = normalize_name(name)

    # direct exact lookup
    if name in company_to_symbol:
        return company_to_symbol[name]
    if name_norm in company_to_symbol:
        return company_to_symbol[name_norm]

    # try exact case-insensitive keys
    for cname, sym in company_to_symbol.items():
        if cname.lower() == name_norm:
            return sym

    if _HAS_RAPIDFUZZ:
        choices = list(company_to_symbol.keys())
        best = process.extractOne(name_norm, choices, scorer=fuzz.WRatio)
        if best and best[1] >= score_threshold:
            return company_to_symbol.get(best[0])
    else:
        for cname, sym in company_to_symbol.items():
            if name_norm in cname.lower() or cname.lower() in name_norm:
                return sym

    return None

def compute_impacts_for_entities(entities: Dict[str, Any],
                                 company_to_symbol: Dict[str, str],
                                 symbol_to_sector: Dict[str, Dict],
                                 regulator_rules: Dict[str, Dict],
                                 policy_rules: Dict[str, Dict],
                                 sector_to_symbols: Dict[str, List[str]] = None,
                                 index_to_symbols: Dict[str, List[str]] = None) -> List[Dict[str, Any]]:
    company_to_symbol = company_to_symbol or {}
    symbol_to_sector = symbol_to_sector or {}
    regulator_rules = regulator_rules or {}
    policy_rules = policy_rules or {}
    sector_to_symbols = sector_to_symbols or {}
    index_to_symbols = index_to_symbols or {}

    impacts_flags = defaultdict(lambda: defaultdict(bool))

    # 1) Direct companies
    for comp in entities.get("companies", []) or []:
        sym = None
        if comp in company_to_symbol:
            sym = company_to_symbol[comp]
            impacts_flags[sym]["gazetteer"] = True
        else:
            sym = fuzzy_match_company(comp, company_to_symbol)
            if sym:
                impacts_flags[sym]["gazetteer"] = True
        if sym:
            impacts_flags[sym]["direct"] = True

    # 2) Sector mentions
    for sector in entities.get("sectors", []) or []:
        key = normalize_name(sector)
        syms = sector_to_symbols.get(key, [])
        for s in syms:
            impacts_flags[s]["sector"] = True

    # 3) Regulator Mention
    for reg in entities.get("regulators", []) or []:
        rkey = normalize_name(reg)

        rule = regulator_rules.get(rkey) or regulator_rules.get(rkey.upper()) or regulator_rules.get(rkey.lower())
        if rule:
            for sec in (rule.get("sectors") or []):
                syms = sector_to_symbols.get(sec.lower(), [])
                for s in syms:
                    impacts_flags[s]["regulatory"] = True

    # 4) Policy mentions
    for policy in entities.get("policies", []) or []:
        pkey = normalize_name(policy)
        rule = policy_rules.get(pkey) or policy_rules.get(pkey.lower())
        if rule:
            for sec in (rule.get("sectors") or []):
                if sec == "All":
                    for s in symbol_to_sector.keys():
                        impacts_flags[s]["policy"] = True
                else:
                    syms = sector_to_symbols.get(sec.lower(), [])
                    for s in syms:
                        impacts_flags[s]["policy"] = True

    # 5) Index mentions
    for idx in entities.get("indices", []) or []:
        idx_key = normalize_name(idx)
        syms = index_to_symbols.get(idx_key, [])
        for s in syms:
            impacts_flags[s]["index"] = True

    # Build final list: compute confidence by priority
    results = []
    for sym, flags in impacts_flags.items():
        primary = None
        for t in PRIORITY_ORDER:
            if flags.get(t):
                primary = t
                break
        if primary is None:
            primary = "semantic"
        conf = float(SCORES.get(primary, 0.4))
        results.append({
            "symbol": sym,
            "confidence": round(conf, 3),
            "type": primary,
            "flags": [k for k, v in flags.items() if v]
        })

    if not results:
        for policy in entities.get("policies", []) or []:
            rule = policy_rules.get(normalize_name(policy))
            if rule:
                for sec in (rule.get("sectors") or []):
                    syms = sector_to_symbols.get(sec.lower(), [])[:5]
                    for s in syms:
                        results.append({"symbol": s, "confidence": round(SCORES["policy"], 3), "type": "policy", "flags": ["policy"]})

    results = sorted(results, key=lambda x: -x["confidence"])
    return results


def format_impacts_list(impacts: List[Dict[str, Any]], max_items: int = 20) -> List[Dict]:
    out = []
    seen = set()
    for it in impacts:
        sym = it["symbol"]
        if sym in seen:
            continue

        seen.add(sym)
        out.append({
            "symbol": sym,
            "confidence": float(it["confidence"]),
            "type": it.get("type", "inferred"),
            "flags": it.get("flags", [])
        })
        
        if len(out) >= max_items:
            break
    return out


if __name__ =="__main__":
    company_to_symbol, symbol_to_sector, reg_rules, pol_rules, sector_to_symbols = load_mapping()

    entities = {
    "companies": ["HDFC Bank"],
    "sectors": ["Banking"],
    "regulators": ["RBI"],
    "policies": ["repo rate"],
    "indices": []
    }

    impacts = compute_impacts_for_entities(entities, company_to_symbol, symbol_to_sector, reg_rules, pol_rules, sector_to_symbols)
    print(impacts[:10])
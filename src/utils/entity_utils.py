import re, json, numpy as np
from pathlib import Path
from typing import List, Dict

gazetteer_path = Path("src/utils/fin_gazetteers.json")

with open(gazetteer_path, "r") as f:
    GAZ = json.load(f)

# print(G)

INDICES = [x.lower() for x in GAZ["indices"]]
SECTORS = [x.lower() for x in GAZ["sectors"]]
REGULATORS = [x.lower() for x in GAZ["regulators"]]
FIN_TERMS = [x.lower() for x in GAZ["financial_terms"]]
KPI_TERMS = [x.lower() for x in GAZ["kpi_terms"]]
COMPANIES_CUSTOM = [x.lower() for x in GAZ["companies_custom"]]
PRODUCTS = [x.lower() for x in GAZ["products"]]

MONEY_REGEX = re.compile(r"(₹\s?\d+[\d,]*(?:\.\d+)?|\b\d+(\.\d+)?\s?(crore|lakh|million|billion))", re.I)
PERCENT_REGEX = re.compile(r"(\b\d+(\.\d+)?\s?%)")
KPI_REGEX = re.compile(r"\b(Q[1-4]\s?(results|earnings)|EBITDA|PAT|EPS|Revenue|Profit)\b", re.I)

def normalize(items):
    seen = set()
    out = []
    for i in items:
        if not i: 
            continue
        key = i.strip().lower()
        if key not in seen:
            seen.add(key)
            out.append(i.strip())
    return out

def longest_match_gazetteer(text: str, entity_list: List):
    """Returns a list of matched phrases using longest-match-first logic."""
    text_lower = text.lower()
    matches = []
    occupied = [False]*len(text_lower)
    sorted_list = sorted(entity_list, key=lambda x: -len(x))

    for entity in sorted_list:
        e_low = entity.lower()
        start_idx = text_lower.find(e_low)
        while start_idx != -1:
            end_idx = start_idx + len(e_low)
            if not any(occupied[start_idx:end_idx]):
                matches.append(entity)

                for i in range(start_idx, end_idx):
                    occupied[i] = True

            start_idx = text_lower.find(e_low, start_idx + 1)
    return list(set(matches))

def match_rules(text):
    tl = text.lower()

    return {
        "indices": normalize(longest_match_gazetteer(text, INDICES)),
        "sectors": normalize([s for s in SECTORS if s in tl]),
        "regulators": normalize([r for r in REGULATORS if r in tl]),
        "policies": normalize([t for t in FIN_TERMS if t in tl]),
        "custom_companies": normalize([c for c in COMPANIES_CUSTOM if c in tl]),
        "products": normalize([p for p in PRODUCTS if p in tl]),
        "kpis": normalize([m.group(0) for m in KPI_REGEX.finditer(text)]),
        "money": normalize([m.group(0) for m in MONEY_REGEX.finditer(text)]),
        "percent": normalize([m.group(0) for m in PERCENT_REGEX.finditer(text)])
    }


# ===========================================
# Merging Entities
# ===========================================

KPI_SET = set([k.lower() for k in KPI_TERMS])
FINTERM_SET = set([k.lower() for k in FIN_TERMS])
REGULATOR_SET = set([k.lower() for k in REGULATORS])
COMPANY_GAZETTEER = set([k.lower() for k in COMPANIES_CUSTOM])

PUNCT_RE = re.compile(r"[^\w\s]")
NUMERIC_RE = re.compile(r"^[\d\W_]+$")   # tokens that are purely numbers/punct

def _clean_span(s: str) -> str:
    """Normalize whitespace and punctuation; keep original casing for display but return cleaned lowered form for checks"""
    if s is None:
        return ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _is_company_token(token: str) -> bool:
    t = token.strip()
    if not t:
        return False
    low = t.lower()
    if low in REGULATOR_SET or low in KPI_SET or low in FINTERM_SET:
        return False
    if NUMERIC_RE.match(low):
        return False
    if len(low) <= 2 and not low.isalpha(): # "Q2"
        return False
    return True

def prioritize_companies(model_orgs: List[str], gaz_companies: List[str], regulators: List[str], kpis: List[str], fin_terms: List[str]) -> List[str]:
    """NER model and gazetteer have an overlap of organizations, companies and regulators.
    This function solves that"""
    chosen = []
    seen = set()

    # Add gazetteer matches
    for c in gaz_companies:
        if not c:
            continue
        clean = _clean_span(c)
        low = clean.lower()
        if low in seen: 
            continue
        if _is_company_token(c):
            chosen.append(clean)
            seen.add(low)

    # Add model ORGs 
    for org in model_orgs:
        if not org:
            continue
        org_clean = _clean_span(org)
        low = org_clean.lower()
        if low in KPI_SET or low in FINTERM_SET or low in REGULATOR_SET:
            continue
        if not _is_company_token(org_clean):
            continue

        # if model org is substring of an existing chosen (eg "HDFC" vs "HDFC Bank"), skip
        is_sub = False
        for already in chosen:
            if org_clean.lower() in already.lower():
                is_sub = True
                break
            if already.lower() in org_clean.lower():
                if already.lower() in seen:
                    chosen = [x for x in chosen if x.lower() != already.lower()]
                    seen.discard(already.lower())
                break
        if not is_sub:
            chosen.append(org_clean)
            seen.add(low)

    # Sort by length
    chosen = sorted(chosen, key=lambda x: -len(x))
    return chosen

def postprocess_entities(model_ner_out: List[Dict], rule_out: Dict):
    # extract raw lists
    model_orgs = [ _clean_span(e["word"]) for e in model_ner_out if e.get("entity_group","").upper() in ("ORG","MISC","MISCELLANEOUS") ]
    model_pers = [ _clean_span(e["word"]) for e in model_ner_out if e.get("entity_group","").upper() in ("PER","PERSON") ]
    model_locs = [ _clean_span(e["word"]) for e in model_ner_out if e.get("entity_group","").upper() in ("LOC","GPE") ]

    # extract gazetteer outputs 
    gaz_companies = rule_out.get("custom_companies", []) or []
    regulators = rule_out.get("regulators", []) or []
    kpis = rule_out.get("kpis", []) or []
    fint = rule_out.get("policies", []) or []
    indices = rule_out.get("indices", []) or []
    sectors = rule_out.get("sectors", []) or []
    products = rule_out.get("products", []) or []
    money = rule_out.get("money", []) or []
    percent = rule_out.get("percent", []) or []

    companies = prioritize_companies(model_orgs, gaz_companies, regulators, kpis, fint)

    for g in gaz_companies:
        if g and g.lower() not in [c.lower() for c in companies]:
            companies.append(_clean_span(g))

    # Deduplication for all lists
    def dedup_list(list):
        out = []
        seen = set()
        for item in list:
            if not item:
                continue
            k = item.strip()
            if k.lower() in seen:
                continue
            seen.add(k.lower())
            out.append(k)
        return out
    
    final = {
        "companies": dedup_list(companies),
        "people": dedup_list(model_pers),
        "locations": dedup_list(model_locs),
        "indices": dedup_list(indices),
        "sectors": dedup_list(sectors),
        "regulators": dedup_list(regulators),
        "policies": dedup_list(fint),
        "products": dedup_list(products),
        "kpis": dedup_list(kpis),
        "money": dedup_list(money),
        "percent": dedup_list(percent)
    }

    final["companies"] = [c for c in final["companies"] if c.lower() not in REGULATOR_SET and c.lower() not in KPI_SET and c.lower() not in FINTERM_SET]

    return final

if __name__ == "__main__":
    sample_text = """
                RBI increased the repo rate by 25 bps leading to volatility in NIFTY 50. 
                HDFC Bank and Reliance saw strong Q2 results with EBITDA growing 12%.
                Investors expect inflation to ease in coming quarters.
                """
    ner_out = [{'entity_group': 'ORG',
                'score': np.float32(0.9991365),
                'word': 'RBI',
                'start': 1,
                'end': 4},
                {'entity_group': 'ORG',
                'score': np.float32(0.9992687),
                'word': 'HDFC Bank',
                'start': 75,
                'end': 84},
                {'entity_group': 'ORG',
                'score': np.float32(0.99848515),
                'word': 'Reliance',
                'start': 89,
                'end': 97},
                {'entity_group': 'ORG',
                'score': np.float32(0.99618524),
                'word': 'EBITDA',
                'start': 125,
                'end': 131}]
    rules = match_rules(sample_text)  
    # print(rules)
    cleaned = postprocess_entities(ner_out, rules)
    print(cleaned)
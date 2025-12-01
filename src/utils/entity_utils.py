import re, json
from pathlib import Path
from typing import List, Dict

gazetteer_path = Path("src/utils/fin_gazetteers.json")

with open(gazetteer_path, "r") as f:
    G = json.load(f)

REGULATORS = [x.lower() for x in G.get("regulators", [])]
INDICES = [x.lower() for x in G.get("indices", [])]
SECTORS = [x.lower() for x in G.get("sectors", [])]
FIN_TERMS = [x.lower() for x in G.get("financial_terms", [])]
KPI_TERMS = [x.lower() for x in G.get("kpi_terms", [])]
PRODUCTS = [x.lower() for x in G.get("products", [])]
COMPANIES_CUSTOM = [x.lower() for x in G.get("companies_custom", [])]

MONEY_REGEX = re.compile(r"(₹\s?\d+[\d,]*(?:\.\d+)?|\b\d+(\.\d+)?\s?(crore|lakh|million|billion))", re.I)
PERCENT_REGEX = re.compile(r"(\b\d+(\.\d+)?\s?%)")
KPI_REGEX = re.compile(r"\b(Q[1-4]\s?(results|earnings)|EBITDA|PAT|EPS|Revenue|Profit)\b", re.I)

def normalize_list(items):
    out = []
    seen = set()
    for it in items:
        if not it:
            continue
        s = re.sub(r"\s+", " ", it.strip())
        if s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out

def rule_match(text: str):
    text = text.lower()

    found = {
        "indices": [i for i in INDICES if i in text],
        "sectors": [i for i in SECTORS if i in text],
        "regulators": [i for i in REGULATORS if i in text],
        "policies": [i for i in FIN_TERMS if i in text],
        "products": [i for i in PRODUCTS if i in text],
        "custom_companies": [i for i in COMPANIES_CUSTOM if i in text],
        "kpis": list(set(m.group(0) for m in KPI_REGEX.finditer(text))),
        "money": list(set(m.group(0) for m in MONEY_REGEX.finditer(text))),
        "percent": list(set(m.group(0) for m in PERCENT_REGEX.finditer(text))),
    }

    for k in found:
        found[k] = normalize_list(found[k])

    return found
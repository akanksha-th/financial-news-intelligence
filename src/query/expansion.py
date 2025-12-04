import json, os
from typing import Dict, List
from pathlib import Path

ASSETS = Path("assets")
FIN_GAZ = ASSETS / "fin_gazetteers.json"
COMPANY_TO_SYMBOL = ASSETS / "company_to_symbol.json"
SECTOR_TO_SYMBOLS = ASSETS / "sector_to_symbols.json"
SYMBOL_TO_SECTOR = ASSETS / "symbol_to_sector.json"
REGULATOR_RULES = ASSETS / "regulator_impact_rules.json"
POLICY_RULES = ASSETS / "policy_impact_rules.json"

def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_company2sym = _load(COMPANY_TO_SYMBOL)
_sector2syms = _load(SECTOR_TO_SYMBOLS)
_sym2meta = _load(SYMBOL_TO_SECTOR)
_reg_rules = _load(REGULATOR_RULES)
_pol_rules = _load(POLICY_RULES)
_fin_gaz = _load(FIN_GAZ)

def expand_entities_to_assets(entities: Dict[str, List[str]]) -> Dict:
    syms = set()
    sectors = set()
    regs = set()
    pols = set()

    # 1) companies
    for c in entities.get("companies", []):
        sym = _company2sym.get(c) or _company2sym.get(c.lower()) or _company2sym.get(c.upper())
        if not sym:
            for k, v in _company2sym.items():
                if isinstance(v, str) and c.lower() == v.lower():
                    sym = k
                    break
        if not sym:
            fin_companies = _fin_gaz.get("companies_custom") or []
            for name in fin_companies:
                if name.lower() in c.lower() or c.lower() in name.lower():
                    sym = _company2sym.get(name) or _company2sym.get(name.lower()) or None
                    if sym:
                        break
        if sym:
            syms.add(sym)
            meta = _sym2meta.get(sym, {})
            if meta.get("sector"):
                sectors.add(meta.get("sector"))

    # 2) sectors -> grab all symbols from sector_to_symbols
    for s in entities.get("sectors", []):
        key = s.lower()
        syms_from_sector = _sector2syms.get(key) or _sector2syms.get(s) or []
        for sym in syms_from_sector:
            syms.add(sym)
        if syms_from_sector:
            sectors.add(s)

    # 3) regulators -> use regulator rules file if present, else consult fin_gaz
    for r in entities.get("regulators", []):
        rk = r.lower()
        rule = _reg_rules.get(rk) or _reg_rules.get(r.upper())
        if not rule:
            # fallback: fin_gaz might contain regulator -> sectors mapping under a different key
            alt = _fin_gaz.get("regulator_to_sectors") or {}
            rule = {"sectors": alt.get(rk, [])} if rk in alt else None
        if rule:
            for sec in rule.get("sectors", []):
                syms_from_sector = _sector2syms.get(sec.lower(), [])
                for sym in syms_from_sector:
                    syms.add(sym)
                sectors.add(sec)
            regs.add(r)

    # 4) policies -> map to sectors using policy_rules or fin_gaz
    for p in entities.get("policies", []):
        pk = p.lower()
        rule = _pol_rules.get(pk) or _pol_rules.get(p)
        if not rule:
            # check fin_gazer
            alt = _fin_gaz.get("policy_to_sectors") or {}
            if pk in alt:
                rule = {"sectors": alt[pk], "confidence": 0.6}
        if rule:
            for sec in (rule.get("sectors") or []):
                for sym in _sector2syms.get(sec.lower(), []):
                    syms.add(sym)
                sectors.add(sec)
            pols.add(p)

    indices = entities.get("indices", [])

    return {
        "symbols": list(sorted(syms)),
        "sectors": list(sorted(sectors)),
        "regulators": list(sorted(regs)),
        "policies": list(sorted(pols)),
        "indices": indices
    }

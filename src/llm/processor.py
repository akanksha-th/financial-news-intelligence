from src.llm.rewriter import LocalLLM
from src.utils.entity_utils import match_rules, postprocess_entities
from src.utils.impact_mapping import load_mapping, compute_impacts_for_entities

class QueryProcessor:
    def __init__(self, model_path):
        self.llm = LocalLLM(model_path=model_path)

    def process(self, user_query: str) -> dict:
        """
        Pipeline:
        1. Rewrite query
        2. Extract JSON intent
        3. Return structured query
        """
        rewritten = self.llm.rewrite(user_query)
        structured = self.llm.structured(user_query)
        structured["rewritten"] = rewritten
        print(rewritten)
        print("query rewritten\n")

        entities = postprocess_entities([], match_rules(rewritten))
        structured["entities"] = entities
        print(entities)
        print("Entities extracted\n")

        def classify_query_type(entities: dict) -> str:
            if entities.get("companies"):
                return "company"
            if entities.get("sectors"):
                return "sector"
            if entities.get("regulators"):
                return "regulator"
            if entities.get("policies"):
                return "policy"
            if entities.get("indices"):
                return "index"
            return "unknown"
        impacts = classify_query_type(entities)
        structured["query_type"] = impacts
        print(impacts)
        print("Query type extracted\n")

        def extract_time_horizon(query: str) -> str:
            q = query.lower()
            if any(w in q for w in ["today", "now", "immediately", "short term"]):
                return "short"
            if any(w in q for w in ["quarter", "this year", "medium term"]):
                return "medium"
            if any(w in q for w in ["long term", "future outlook", "next 5 years"]):
                return "long"
            return "short"
        
        time_hor = extract_time_horizon(rewritten)
        structured["time_horizon"] = time_hor
        return structured
    

if __name__ == "__main__":
    model_path = "C:/Users/aktkr/financial-news-intelligence/models"
    pr = QueryProcessor(model_path)
    query = "RBI raised repo rate, who will benefit?"
    print(pr.process(query))
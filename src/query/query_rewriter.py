import openai, os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("API_KEY")

class QueryRewriter:
    def __init__(self, api_key: str = OPENAI_API_KEY):
        self.client = openai.OpenAI(api_key=api_key)

    def rewrite(self, query: str) -> str:
        """Returns a rewritten, clean, expanded query string."""
        prompt = f"""
        Rewrite the following financial query into a clean, search-optimized form.
        Preserve all financial intent. Expand tickers into company names where possible.

        Query: "{query}"

        Return only the rewritten query. No explanation.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens = 80
        )

        return response.choices[0].message.content.strip()
    
    def rewrite_with_intent(self, query: str) -> dict:
        """
        Return structured output:
        {
            "rewritten": "...",
            "intent": "...",
            "query_type": "...",
            "time_horizon": "short/medium/long",
        }
        """

        prompt = f"""
        Analyze this financial query and return structured JSON.

        Query: "{query}"

        Return a JSON with:
        - rewritten: cleaned & expanded query
        - intent: (impact, sentiment, price movement, macro, sector analysis, etc.)
        - query_type: (company, sector, macro, regulator, policy)
        - time_horizon: short / medium / long

        Return ONLY valid JSON. Nothing else.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )

        import json
        return json.loads(response.choices[0].message.content.strip())
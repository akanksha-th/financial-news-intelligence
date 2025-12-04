from gpt4all import GPT4All
import json

class LocalLLM:
    def __init__(self, model_path):
        self.llm = GPT4All(model_path=model_path, model_name="phi-2.Q4_0.gguf", allow_download=False)

    def ask(self, prompt: str, max_tokens: int = 256) -> str:
        return self.llm.generate(prompt, max_tokens=max_tokens).strip()

    def rewrite(self, query: str) -> str:
        from src.llm.prompts import QUERY_REWRITE_PROMPT
        prompt = QUERY_REWRITE_PROMPT.format(query=query)
        return self.ask(prompt)

    def structured(self, query: str) -> dict:
        from src.llm.prompts import STRUCTURED_QUERY_PROMPT
        prompt = STRUCTURED_QUERY_PROMPT.format(query=query)

        raw = self.ask(prompt, max_tokens=256)

        # remove code fences if GPT4All adds them
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(raw)
        except Exception:
            return {
                "rewritten": query,
                "query_type": "unknown",
                "entities": [],
                "time_horizon": "short"
            }

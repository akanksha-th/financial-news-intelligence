# src/query/search.py
"""
Embedding-based retrieval from your news database.
This assumes you have precomputed embeddings for stories and stored them either in:
 - a local file mapping story_id -> embedding (np array) OR
 - in the DB with an 'embedding' column (serialized)

We will provide a simple file-based fallback: store embeddings under data/embeddings.npy
and metadata in data/embeddings_meta.json

We use sentence-transformers to embed query and do cosine similarity.
"""

import os, json, numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, util
from datetime import datetime, timedelta

# Use a small model that runs on CPU
_EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None

# paths for fallback storage
EMB_DIR = "data"
EMB_META = os.path.join(EMB_DIR, "embeddings_meta.json")   # list of {"story_id":..,"text":..,"published_at":..}
EMB_ARRAY = os.path.join(EMB_DIR, "embeddings.npy")        # NxD float32

def load_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(_EMB_MODEL_NAME)
    return _model

def load_embeddings_from_files():
    """
    Returns (meta_list, embeddings_array) where meta_list is list of dicts with story_id, text, published_at
    """
    if not os.path.exists(EMB_META) or not os.path.exists(EMB_ARRAY):
        return [], None
    with open(EMB_META, "r", encoding="utf-8") as f:
        meta = json.load(f)
    arr = np.load(EMB_ARRAY)
    return meta, arr

def search(query: str, top_k: int = 10, expanded_symbols: List[str] = None) -> List[Dict[str, Any]]:
    """
    1. embed query
    2. compute cosine similarity against precomputed story embeddings
    3. optionally boost scores for stories that mention expanded_symbols (if story metadata contains them)
    """
    model = load_model()
    q_emb = model.encode(query, convert_to_numpy=True)

    meta, arr = load_embeddings_from_files()
    if arr is None or len(meta) == 0:
        return []

    # cosine sim
    sims = util.cos_sim(q_emb, arr)[0].cpu().numpy()  # vector of sims
    # Build results list
    results = []
    for i, m in enumerate(meta):
        score = float(sims[i])
        # recency boost: if published within 7 days add small bonus
        pub = m.get("published_at")
        try:
            if pub:
                # parse if ISO-like
                dt = datetime.fromisoformat(pub)
                days = (datetime.utcnow() - dt).days
                if days < 7:
                    score += 0.05
        except Exception:
            pass

        # symbol boost: if story mentions any expanded_symbols, add bonus
        if expanded_symbols:
            story_text = m.get("text", "").lower()
            for s in expanded_symbols:
                if s.lower() in story_text:
                    score += 0.1

        results.append({"story_id": m["story_id"], "score": score, "meta": m})

    # sort
    results = sorted(results, key=lambda x: -x["score"])
    return results[:top_k]

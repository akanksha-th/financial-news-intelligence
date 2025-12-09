import os
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

try:
    import faiss
    _HAS_FAISS = True
except Exception:
    faiss = None
    _HAS_FAISS = False

MODEL_NAME = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
EMBED_DIR = Path("embeddings")
EMBED_DIR.mkdir(parents=True, exist_ok=True)
EMBED_FILE = EMBED_DIR / "story_embeddings.npy"
META_FILE = EMBED_DIR / "story_metadata.json"
INDEX_FILE = EMBED_DIR / "faiss.index"

class EmbeddingIndex:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.ids = []  
        self.vectors = None

    def build_from_stories(self, stories: list, text_key="combined_text", id_key="id", batch_size=64, save=True):
        """
        stories: list of dicts {id, combined_text, article_title, published_at, ...}
        will compute embeddings and build index
        """
        texts = [s.get(text_key, "") or "" for s in stories]
        ids = [s[id_key] for s in stories]

        all_vecs = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding"):
            batch = texts[i:i+batch_size]
            vecs = self.model.encode(batch, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
            all_vecs.append(vecs)
        all_vecs = np.vstack(all_vecs).astype("float32")

        self.vectors = all_vecs
        self.ids = ids

        if _HAS_FAISS:
            dim = all_vecs.shape[1]
            idx = faiss.IndexFlatIP(dim)
            idx.add(all_vecs)
            self.index = idx
            if save:
                faiss.write_index(idx, str(INDEX_FILE))
        else:
            self.index = None
            if save:
                np.save(EMBED_FILE, all_vecs)

        if save:
            with open(META_FILE, "w", encoding="utf-8") as f:
                json.dump([{"id": int(i), "title": s.get("article_title"), "published_at": str(s.get("published_at"))} for i, s in zip(ids, stories)], f, indent=2)

    def save(self):
        if self.vectors is not None:
            np.save(EMBED_FILE, self.vectors)
            with open(META_FILE, "w", encoding="utf-8") as f:
                json.dump([{"id": int(i)} for i in self.ids], f, indent=2)
        if _HAS_FAISS and self.index is not None:
            faiss.write_index(self.index, str(INDEX_FILE))

    def load(self):
        if _HAS_FAISS and INDEX_FILE.exists():
            idx = faiss.read_index(str(INDEX_FILE))
            self.index = idx
            if META_FILE.exists():
                with open(META_FILE, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                self.ids = [m["id"] for m in meta]
        elif EMBED_FILE.exists():
            self.vectors = np.load(str(EMBED_FILE))

            if META_FILE.exists():
                with open(META_FILE, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                self.ids = [m["id"] for m in meta]
        else:
            raise FileNotFoundError("No index or embeddings found. Build index first.")

    def query(self, query_text: str, top_k: int = 10):
        qvec = self.model.encode([query_text], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        if _HAS_FAISS and self.index is not None:
            D, I = self.index.search(qvec, top_k)
            scores = D[0].tolist()
            idxs = I[0].tolist()
            results = []
            for sc, ix in zip(scores, idxs):
                sid = self.ids[ix]
                results.append({"id": sid, "score": float(sc)})
            return results
        else:
            mat = self.vectors  # shape (N, d)
            cos = util.cos_sim(qvec, mat)[0]  # shape (N,)
            top = np.argsort(-cos)[:top_k]
            results = []
            for ix in top:
                results.append({"id": int(self.ids[ix]), "score": float(cos[ix])})
            return results

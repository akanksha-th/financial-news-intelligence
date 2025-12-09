from .embedding_index import EmbeddingIndex
from src.core.database import fetch_unique_stories

if __name__ == "__main__":
    # run on CLI using "python -m src.core.build_embeddings"

    print("Fetching all unique stories from DB...")
    stories = fetch_unique_stories()

    print(f"Loaded {len(stories)} stories.")
    if len(stories) == 0:
        raise RuntimeError("No stories found! Cannot build embeddings.")

    print("Building embeddings...")
    idx = EmbeddingIndex()
    idx.build_from_stories(stories, text_key="combined_text", id_key="id", batch_size=64, save=True)

    print("Embedding index built successfully!")
    print("Files generated in ./embeddings/")

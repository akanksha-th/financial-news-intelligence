from src.core.database import fetch_unique_stories
from src.search.embedding_index import EmbeddingIndex

stories = fetch_unique_stories()
ei = EmbeddingIndex()
ei.build_from_stories(stories, text_key="combined_text", id_key="id")
ei.save()
print("Built embeddings and saved to disk.")

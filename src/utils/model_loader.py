import os 
from pathlib import Path
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline
)

def get_snapshot_folder(local_dir: str):
    """Find the actual model snapshot folder inside Huggingface cache."""
    base = Path(local_dir)
    snapshot_dirs = list(base.glob("**/snapshots/*"))
    if len(snapshot_dirs) == 0:
        return None
    return snapshot_dirs[0]

def load_local_or_download(model_name: str, local_dir: str, task: str = "ner"):
    """Loads a HuggingFace model from local directory, if exists. Otherwise downloads and caches it."""
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"  # Fix Windows symlink issue

    snapshot = get_snapshot_folder(local_dir)

    if snapshot:
        print(f"[Model Loader] Loading model locally from {snapshot}.")
        tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
        model = AutoModelForTokenClassification.from_pretrained(snapshot, local_files_only=True)

    else:
        print(f"[Model Loader] Local model not found. Downloading {model_name} ...")
        tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=local_dir)
        model = AutoModelForTokenClassification.from_pretrained(model_name, cache_dir=local_dir)
        print(f"[Model Loader] Model downloaded and cached at {local_dir}")

    return pipeline(
        task,
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple"
    )

"""E5 product embeddings; model files and vectors stay in the project cache."""

import hashlib
import json
from pathlib import Path


MODEL_NAME = "intfloat/multilingual-e5-small"
CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "recommendation"


def e5_vectors(products: dict, cache_dir: Path = CACHE_DIR) -> dict:
    ids = sorted(products)
    if not ids:
        return {}
    # Symmetric product-to-product similarity: E5 requires query: on both sides.
    texts = ["query: " + products[pid]["embedding_text"] for pid in ids]
    signature = hashlib.sha256(json.dumps(
        [MODEL_NAME, ids, texts], ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    cache_dir = Path(cache_dir)
    vector_file = cache_dir / f"vectors-{signature}.json"
    if vector_file.exists():
        vectors = json.loads(vector_file.read_text(encoding="utf-8"))
    else:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "E5 requires sentence-transformers. Run: python -m pip install -r requirements.txt"
            ) from exc
        cache_dir.mkdir(parents=True, exist_ok=True)
        model = SentenceTransformer(
            MODEL_NAME, cache_folder=str(cache_dir / "models"), device="cpu",
        )
        vectors = model.encode(
            texts, batch_size=32, normalize_embeddings=True, show_progress_bar=True,
        ).tolist()
        vector_file.write_text(json.dumps(vectors), encoding="utf-8")
    if len(vectors) != len(ids) or any(len(vector) != 384 for vector in vectors):
        raise ValueError(f"Invalid E5 vector cache: {vector_file}")
    return {pid: dict(enumerate(vector)) for pid, vector in zip(ids, vectors)}

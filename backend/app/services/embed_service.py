"""Singleton wrapper for the local sentence-transformers embedding model.

Loaded once at app startup via load_model(), then reused for every
query embedding at request time. Encoding runs in a thread pool so it
never blocks the async event loop.
"""

import asyncio
import logging

from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
DIMS = 384

_model: SentenceTransformer | None = None


def load_model() -> None:
    """Load the model into memory. Call once at app startup."""
    global _model
    log.info("Loading embedding model %s …", MODEL_NAME)
    _model = SentenceTransformer(MODEL_NAME)
    log.info("Embedding model ready. Dims: %d", DIMS)


def get_model() -> SentenceTransformer:
    if _model is None:
        raise RuntimeError("Embedding model not loaded — call load_model() at startup")
    return _model


async def embed_query(text: str) -> list[float]:
    """Embed a single query string. Runs model.encode in a thread."""
    model = get_model()
    vec = await asyncio.to_thread(
        model.encode, text, convert_to_numpy=True, show_progress_bar=False
    )
    return vec.tolist()

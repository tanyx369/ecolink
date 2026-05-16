import os

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            import vertexai
            from vertexai.language_models import TextEmbeddingModel
            vertexai.init(
                project=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
                location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            )
            _model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        except Exception as e:
            print(f"[Vertex AI] init error: {e}")
            _model = None
    return _model


def embed_actor(actor: dict) -> list[float]:
    text = (
        f"{actor.get('name', '')}. "
        f"Type: {actor.get('type', '')}. "
        f"Sectors: {', '.join(actor.get('sectors', []))}. "
        f"Tags: {', '.join(actor.get('expertise_tags', []))}. "
        f"Bio: {actor.get('bio', actor.get('description', ''))}"
    )
    try:
        model = _get_model()
        if model is None:
            return _fallback_embedding(text)
        result = model.get_embeddings([text])
        return result[0].values
    except Exception as e:
        print(f"[Vertex AI] embed_actor error: {e} — using fallback")
        return _fallback_embedding(text)


def _fallback_embedding(text: str) -> list[float]:
    """Deterministic pseudo-embedding when Vertex AI is unavailable."""
    import hashlib
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    rng_state = seed
    result = []
    for _ in range(768):
        rng_state = (rng_state * 1664525 + 1013904223) & 0xFFFFFFFF
        result.append((rng_state / 0xFFFFFFFF) * 2 - 1)
    mag = sum(x ** 2 for x in result) ** 0.5
    return [x / mag for x in result] if mag else result


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x ** 2 for x in a) ** 0.5
    mag_b = sum(x ** 2 for x in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0

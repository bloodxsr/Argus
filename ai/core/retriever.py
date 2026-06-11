from __future__ import annotations

from typing import List, Tuple

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as q_models
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional deps
    QdrantClient = None  # type: ignore
    q_models = None
    SentenceTransformer = None  # type: ignore

from .knowledge import KnowledgeSnippet, SecurityKnowledgeBase


class QdrantRetriever:
    def __init__(self, url: str = "127.0.0.1", port: int = 6333, collection_name: str = "security_kb") -> None:
        self.url = url
        self.port = port
        self.collection_name = collection_name
        self.client = None
        self.embedder = None
        if QdrantClient is not None:
            try:
                self.client = QdrantClient(url=self.url, port=self.port)
            except Exception:
                self.client = None
        if SentenceTransformer is not None:
            try:
                self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self.embedder = None

        # fallback knowledge base when external services are unavailable
        self._fallback_kb = SecurityKnowledgeBase()

    def ingest_snippets(self, snippets: List[KnowledgeSnippet]) -> None:
        if not self.client or not q_models:
            return
        # ensure collection exists
        # Qdrant client will create collections on upsert if needed
        vectors = [self._embed_text(s.title + " " + s.summary) for s in snippets]
        payload = []
        for i, s in enumerate(snippets):
            payload.append(
                q_models.PointStruct(id=i, vector=vectors[i], payload={"title": s.title, "summary": s.summary, "mitre": s.mitre_techniques, "action": s.recommended_action})
            )
        try:
            self.client.upsert(self.collection_name, points=payload)
        except Exception:
            return

    def search(self, query: str, limit: int = 5) -> Tuple[KnowledgeSnippet, ...]:
        # If embedder and client available, query qdrant
        if self.client and self.embedder and q_models:
            vec = self._embed_text(query)
            try:
                hits = self.client.search(collection_name=self.collection_name, query_vector=vec, limit=limit)
                snippets = []
                for h in hits:
                    p = h.payload
                    snippets.append(
                        KnowledgeSnippet(
                            title=p.get("title", ""),
                            summary=p.get("summary", ""),
                            markers=tuple(),
                            mitre_techniques=tuple(p.get("mitre", ())),
                            recommended_action=p.get("action", "observe"),
                        )
                    )
                return tuple(snippets)
            except Exception:
                return tuple(self._fallback_kb.retrieve_from_text(query, limit=limit))
        # fallback to in-memory KB
        return tuple(self._fallback_kb.retrieve_from_text(query, limit=limit))

    def _embed_text(self, text: str) -> List[float]:
        if self.embedder:
            return self.embedder.encode(text).tolist()
        # cheap deterministic fallback: character-based hashing to fixed-size vector
        vec = [0.0] * 128
        for i, ch in enumerate(text[:1024]):
            vec[i % 128] += ord(ch) % 13
        return vec

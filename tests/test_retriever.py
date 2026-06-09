from unittest import TestCase

from security_ai_service.retriever import QdrantRetriever


class RetrieverFallbackTests(TestCase):
    def test_search_falls_back_to_kb(self) -> None:
        r = QdrantRetriever()
        res = r.search("scheduled backup on host", limit=2)
        # fallback should return at least one KnowledgeSnippet
        self.assertTrue(len(res) >= 1)

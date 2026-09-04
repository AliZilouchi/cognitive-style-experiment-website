import sys
import types
import unittest
from unittest.mock import patch

from sepid_rag.embeddings import OpenRouterEmbeddings, TogetherEmbeddings


class _Item:
    def __init__(self, index, embedding):
        self.index = index
        self.embedding = embedding


class _EmbeddingsApi:
    def __init__(self, values):
        self.values = values

    def create(self, **_kwargs):
        return types.SimpleNamespace(
            data=[_Item(index, value) for index, value in enumerate(self.values)]
        )


class TogetherEmbeddingTests(unittest.TestCase):
    def _backend(self, values, dimension):
        captured = {}

        class FakeTogether:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                self.embeddings = _EmbeddingsApi(values)

        module = types.SimpleNamespace(Together=FakeTogether)
        with patch.dict(sys.modules, {"together": module}):
            backend = TogetherEmbeddings(
                "example/model",
                "secret",
                "freeze-date",
                dimension,
            )
        return backend, captured

    def test_disables_sdk_retries_and_validates_dimension(self):
        backend, captured = self._backend([[3.0, 4.0]], 2)
        vector = backend.embed_query("پرسش")
        self.assertEqual(captured["max_retries"], 0)
        self.assertEqual(captured["timeout"], 30)
        self.assertAlmostEqual(float(vector[0]), 0.6)
        self.assertAlmostEqual(float(vector[1]), 0.8)

    def test_rejects_unexpected_hosted_dimension(self):
        backend, _ = self._backend([[1.0, 2.0, 3.0]], 2)
        with self.assertRaisesRegex(RuntimeError, "frozen count/dimension"):
            backend.embed_query("پرسش")


class OpenRouterEmbeddingTests(unittest.TestCase):
    def _backend(self, values, dimension=2):
        captured = {}

        class FakeOpenAI:
            def __init__(self, **kwargs):
                captured["client"] = kwargs
                self.embeddings = _EmbeddingsApi(values)

        module = types.SimpleNamespace(OpenAI=FakeOpenAI)
        with patch.dict(sys.modules, {"openai": module}):
            backend = OpenRouterEmbeddings(
                "intfloat/multilingual-e5-large",
                "secret",
                "https://openrouter.ai/api/v1",
                "freeze-date",
                dimension,
                "https://study.example.com",
                "Cognitive Style Experiment",
            )
        return backend, captured

    def test_uses_openrouter_without_retries_and_normalizes_vectors(self):
        backend, captured = self._backend([[3.0, 4.0]])
        vector = backend.embed_query("query: پرسش")
        self.assertEqual(captured["client"]["max_retries"], 0)
        self.assertEqual(
            captured["client"]["base_url"], "https://openrouter.ai/api/v1"
        )
        self.assertEqual(
            captured["client"]["default_headers"]["HTTP-Referer"],
            "https://study.example.com",
        )
        self.assertAlmostEqual(float(vector[0]), 0.6)
        self.assertAlmostEqual(float(vector[1]), 0.8)

    def test_rejects_unexpected_openrouter_dimension(self):
        backend, _ = self._backend([[1.0, 2.0, 3.0]])
        with self.assertRaisesRegex(RuntimeError, "frozen count/dimension"):
            backend.embed_query("query: پرسش")

    def test_batches_large_document_sets(self):
        call_sizes = []

        class DynamicEmbeddingsApi:
            def create(self, **kwargs):
                texts = kwargs["input"]
                call_sizes.append(len(texts))
                return types.SimpleNamespace(
                    data=[_Item(index, [3.0, 4.0]) for index, _ in enumerate(texts)]
                )

        class FakeOpenAI:
            def __init__(self, **_kwargs):
                self.embeddings = DynamicEmbeddingsApi()

        module = types.SimpleNamespace(OpenAI=FakeOpenAI)
        with patch.dict(sys.modules, {"openai": module}):
            backend = OpenRouterEmbeddings(
                "intfloat/multilingual-e5-large",
                "secret",
                "https://openrouter.ai/api/v1",
                "freeze-date",
                2,
                document_batch_size=16,
            )

        matrix = backend.embed_documents([f"passage: {index}" for index in range(35)])
        self.assertEqual(call_sizes, [16, 16, 3])
        self.assertEqual(matrix.shape, (35, 2))


if __name__ == "__main__":
    unittest.main()

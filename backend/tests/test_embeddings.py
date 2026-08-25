import sys
import types
import unittest
from unittest.mock import patch

from sepid_rag.embeddings import TogetherEmbeddings


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


if __name__ == "__main__":
    unittest.main()

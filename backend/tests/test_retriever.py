from pathlib import Path
import tempfile
import unittest

from sepid_rag.corpus import load_allowlisted_corpus
from sepid_rag.embeddings import HashingEmbeddings
from sepid_rag.retriever import CorpusRetriever


ROOT = Path(__file__).resolve().parents[1]


class RetrieverTests(unittest.TestCase):
    def test_returns_fixed_number_with_metadata(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        with tempfile.TemporaryDirectory() as directory:
            retriever = CorpusRetriever(
                documents,
                HashingEmbeddings(256),
                top_k=3,
                index_dir=Path(directory),
                score_margin=2.0,
            )
            results = retriever.search("هتل صدف چقدر هزینه دارد؟", "task_1")
            self.assertEqual(len(results), 3)
            self.assertEqual([item.rank for item in results], [1, 2, 3])
            self.assertTrue(all(item.source_id.startswith("S") for item in results))
            self.assertTrue(all(item.chunk_id.startswith(item.source_id) for item in results))
            self.assertTrue(all("task_1" in documents[next(i for i, d in enumerate(documents) if d.chunk_id == item.chunk_id)].task_ids for item in results))
            self.assertEqual(len(list(Path(directory).glob("*.npz"))), 1)

    def test_task_filter_prevents_cross_task_retrieval(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        retriever = CorpusRetriever(
            documents,
            HashingEmbeddings(256),
            top_k=5,
            score_margin=2.0,
        )
        results = retriever.search("هتل و سفر", "task_3")
        self.assertTrue(results)
        self.assertTrue(all(11 <= int(item.source_id[1:]) <= 18 for item in results))


if __name__ == "__main__":
    unittest.main()

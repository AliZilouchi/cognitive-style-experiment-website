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
                top_k=5,
                index_dir=Path(directory),
            )
            results = retriever.search("هتل صدف چقدر هزینه دارد؟")
            self.assertEqual(len(results), 5)
            self.assertEqual([item.rank for item in results], [1, 2, 3, 4, 5])
            self.assertTrue(all(item.source_id.startswith("S") for item in results))
            self.assertEqual(len(list(Path(directory).glob("*.npz"))), 1)


if __name__ == "__main__":
    unittest.main()


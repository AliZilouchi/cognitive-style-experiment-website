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
            self.assertTrue(all(item.source_id.startswith(("S", "E")) for item in results))
            self.assertTrue(all(item.source_ids for item in results))
            self.assertTrue(
                all(item.node_type in {"index", "fact", "comparison", "source"} for item in results)
            )
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
        by_chunk = {item.chunk_id: item for item in documents}
        self.assertTrue(all("task_3" in by_chunk[item.chunk_id].task_ids for item in results))

    def test_broad_questions_pin_manual_coverage_chunks(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        retriever = CorpusRetriever(
            documents,
            HashingEmbeddings(256),
            top_k=3,
            score_margin=0.12,
        )
        accommodation = retriever.search("چه گزینه‌های اقامتی وجود دارد؟", "task_1")
        self.assertEqual(accommodation[0].chunk_id, "T1-INDEX-ACCOMMODATION")
        comparison = retriever.search(
            "سه بازه را از نظر هزینه، هوا و جاذبه‌ها مقایسه کن",
            "task_2",
        )
        self.assertEqual(
            {item.chunk_id for item in comparison},
            {
                "T2-COMPARE-COST",
                "T2-COMPARE-WEATHER",
                "T2-COMPARE-ATTRACTIONS-ALL",
            },
        )

    def test_broad_accommodation_request_covers_overview_and_comparisons(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        retriever = CorpusRetriever(
            documents,
            HashingEmbeddings(256),
            top_k=3,
            score_margin=2.0,
        )
        results = retriever.search(
            "گزینه های اقامت را همراه ویژگی هایشان بده و مقایسه کلی کن",
            "task_1",
        )
        self.assertEqual(
            {item.chunk_id for item in results},
            {
                "T1-INDEX-ACCOMMODATION",
                "T1-COMPARE-COST-CAPACITY",
                "T1-COMPARE-RULES",
            },
        )

    def test_new_public_topics_pin_their_atomic_chunks(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        retriever = CorpusRetriever(
            documents,
            HashingEmbeddings(256),
            top_k=3,
            score_margin=2.0,
        )
        cases = {
            "مردم جزیره چه زبانی دارند و چطور با بومیان ارتباط بگیریم؟": "SHARED-FACT-LANGUAGE-COMMUNICATION",
            "امکانات پزشکی و درمانی جزیره چیست؟": "SHARED-FACT-MEDICAL-SERVICES",
            "جزیره فرودگاه دارد و چطور به آن برسیم؟": "SHARED-FACT-ISLAND-ACCESS",
            "شرایط سیاسی و اداره جزیره چگونه است؟": "SHARED-FACT-POLITICAL-GOVERNANCE",
        }
        for query, expected_chunk in cases.items():
            with self.subTest(query=query):
                self.assertIn(
                    expected_chunk,
                    {item.chunk_id for item in retriever.search(query, None)},
                )


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import unittest

from sepid_rag.corpus import load_allowlisted_corpus


ROOT = Path(__file__).resolve().parents[1]


class CorpusTests(unittest.TestCase):
    def test_exactly_the_allowlisted_sources_load(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        self.assertEqual(len(documents), 100)
        self.assertEqual(
            {source_id for item in documents for source_id in item.source_ids},
            {f"S{i:02d}" for i in range(1, 19)} | {f"E{i:02d}" for i in range(1, 13)},
        )
        self.assertEqual(len({item.chunk_id for item in documents}), len(documents))
        self.assertTrue(all(item.task_ids for item in documents))
        self.assertTrue(
            all(item.node_type in {"index", "fact", "comparison", "source"} for item in documents)
        )
        self.assertTrue(all("evaluation/" not in item.relative_path for item in documents))

    def test_all_original_sources_are_available_as_fallbacks(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        fallback = [item for item in documents if item.node_type == "source"]
        self.assertEqual(len(fallback), 30)
        self.assertEqual(
            {item.source_id for item in fallback},
            {f"S{i:02d}" for i in range(1, 19)} | {f"E{i:02d}" for i in range(1, 13)},
        )
        self.assertTrue(all(item.text.startswith("# ") for item in fallback))

    def test_task_scope_matches_the_three_swts_tasks(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        by_id = {item.chunk_id: item for item in documents}
        self.assertEqual(by_id["SHARED-OVERVIEW-01"].task_ids, ("task_1", "task_2"))
        self.assertEqual(by_id["T1-INDEX-ACCOMMODATION"].task_ids, ("task_1",))
        self.assertEqual(by_id["T2-COMPARE-WEATHER"].task_ids, ("task_2",))
        self.assertEqual(by_id["T3-INDEX-SITUATIONS"].task_ids, ("task_3",))

    def test_accommodation_index_names_all_five_options(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        index = next(item for item in documents if item.chunk_id == "T1-INDEX-ACCOMMODATION")
        self.assertEqual(
            set(index.entities),
            {
                "هتل صدف",
                "مهمان‌خانه موج",
                "خانه‌مسافر فانوس",
                "کلبه‌های نارون",
                "اردوگاه چشمه",
            },
        )

    def test_enriched_metadata_documents_are_not_ingested(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        paths = {item.relative_path for item in documents}
        self.assertFalse(any("00_INDEX" in path for path in paths))
        self.assertFalse(any("schema_provenance" in path for path in paths))
        self.assertFalse(any("fictional_additions_register" in path for path in paths))

    def test_task_two_has_cross_period_comparisons(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        chunk_ids = {item.chunk_id for item in documents}
        self.assertTrue(
            {
                "T2-COMPARE-WEATHER",
                "T2-COMPARE-COST",
                "T2-COMPARE-ATTRACTIONS-ALL",
                "T2-COMPARE-ATTRACTIONS-WINTER-SPRING",
                "T2-COMPARE-ATTRACTIONS-SPRING-SUMMER",
                "T2-COMPARE-ATTRACTIONS-AUTUMN",
            }.issubset(chunk_ids)
        )

    def test_enriched_cultural_topics_have_curated_entry_points(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        chunk_ids = {item.chunk_id for item in documents}
        self.assertTrue(
            {
                "T3-FACT-SOCIETY-IMPORTANCE",
                "T3-FACT-BELIEFS",
                "T3-FACT-MYTH-FIGURES",
                "T3-FACT-RITUALS",
                "T3-FACT-SYMBOLS",
                "T3-FACT-NATURE-SENSITIVITY",
            }.issubset(chunk_ids)
        )

    def test_new_public_information_topics_have_atomic_entry_points(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        chunk_ids = {item.chunk_id for item in documents}
        self.assertTrue(
            {
                "SHARED-FACT-LANGUAGE-COMMUNICATION",
                "SHARED-FACT-MEDICAL-SERVICES",
                "SHARED-FACT-GENERAL-CONDITIONS",
                "T2-COMPARE-CROWDING",
                "SHARED-FACT-VISITOR-FEEDBACK",
                "SHARED-FACT-RESIDENCY-MIGRATION",
                "SHARED-FACT-SECURITY-SAFETY",
                "SHARED-FACT-ISLAND-ACCESS",
                "SHARED-FACT-POLITICAL-GOVERNANCE",
            }.issubset(chunk_ids)
        )

    def test_gold_set_contains_the_three_exact_swts_prompts(self):
        path = ROOT / "corpus" / "evaluation" / "retrieval_gold.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        exact = [row for row in rows if row.get("query_type") == "exact_swts_prompt"]
        self.assertEqual(len(exact), 3)
        self.assertEqual(
            {row["task"] for row in exact},
            {"receptive", "critical", "creative"},
        )

    def test_broad_creative_query_labels_all_eight_sources(self):
        path = ROOT / "corpus" / "evaluation" / "retrieval_gold.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        broad = [
            row
            for row in rows
            if row.get("task") == "creative" and row.get("query_type") == "broad"
        ]
        self.assertEqual(len(broad), 1)
        self.assertEqual(
            set(broad[0]["relevant_source_ids"]),
            {f"S{i:02d}" for i in range(11, 19)},
        )


if __name__ == "__main__":
    unittest.main()

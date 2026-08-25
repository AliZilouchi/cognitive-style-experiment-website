import json
from pathlib import Path
import unittest

from sepid_rag.corpus import load_allowlisted_corpus


ROOT = Path(__file__).resolve().parents[1]


class CorpusTests(unittest.TestCase):
    def test_exactly_the_allowlisted_sources_load(self):
        documents = load_allowlisted_corpus(ROOT / "corpus")
        self.assertEqual(len(documents), 18)
        self.assertEqual([item.source_id for item in documents], [f"S{i:02d}" for i in range(1, 19)])
        self.assertTrue(all("evaluation/" not in item.relative_path for item in documents))

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

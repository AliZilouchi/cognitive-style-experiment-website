import unittest

from sepid_rag.graph import build_retrieval_query, retrieval_scope_for_task


class RetrievalQueryTests(unittest.TestCase):
    def test_every_participant_context_searches_the_complete_corpus(self):
        self.assertIsNone(retrieval_scope_for_task("free_chat"))
        self.assertIsNone(retrieval_scope_for_task("task_1"))
        self.assertIsNone(retrieval_scope_for_task("task_2"))
        self.assertIsNone(retrieval_scope_for_task("task_3"))

    def test_clear_standalone_query_is_not_broadened(self):
        query = "قیمت هتل صدف چقدر است؟"
        self.assertEqual(
            build_retrieval_query(
                query,
                [{"role": "user", "content": "آبخوری کجاست؟"}],
                {"هتل صدف"},
            ),
            query,
        )

    def test_referential_follow_up_uses_recent_context(self):
        result = build_retrieval_query(
            "نسبت به بقیه چطور است؟",
            [
                {"role": "user", "content": "درباره اردوگاه چشمه بگو"},
                {"role": "assistant", "content": "هر محل چادر سه نفر ظرفیت دارد."},
            ],
            {"اردوگاه چشمه"},
        )
        self.assertIn("اردوگاه چشمه", result)
        self.assertIn("نسبت به بقیه چطور است؟", result)

    def test_incomplete_short_question_uses_context(self):
        result = build_retrieval_query(
            "و مجوزش؟",
            [{"role": "user", "content": "قیمت کلبه‌های نارون چقدر است؟"}],
            {"کلبه‌های نارون"},
        )
        self.assertIn("کلبه‌های نارون", result)


if __name__ == "__main__":
    unittest.main()

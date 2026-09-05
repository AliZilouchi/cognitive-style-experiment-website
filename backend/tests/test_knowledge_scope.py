from pathlib import Path
import unittest

from sepid_rag.corpus import load_allowlisted_corpus
from sepid_rag.knowledge_scope import KnowledgeScope


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = KnowledgeScope.load(ROOT / "corpus")
        cls.documents = load_allowlisted_corpus(ROOT / "corpus")
        cls.entities = {entity for document in cls.documents for entity in document.entities}

    def test_supported_topic_is_allowed(self):
        decision = self.scope.classify("امکانات پزشکی جزیره چیست؟", self.entities)
        self.assertEqual(decision.classification, "supported")
        self.assertIn("health_safety", decision.topic_ids)

    def test_far_topic_is_closed_without_retrieval(self):
        decision = self.scope.classify("آیا جزیره بورس ارز دیجیتال دارد؟", self.entities)
        self.assertEqual(decision.classification, "outside_world")

    def test_unrecognized_topic_is_closed(self):
        decision = self.scope.classify("سامانه کوانتومی آن چطور کار می‌کند؟", self.entities)
        self.assertEqual(decision.classification, "unknown_topic")

    def test_referential_context_keeps_follow_up_supported(self):
        decision = self.scope.classify(
            "هتل صدف صبحانه دارد. در مورد بقیه چطور؟",
            self.entities,
        )
        self.assertEqual(decision.classification, "supported")
        self.assertIn("accommodation", decision.topic_ids)

    def test_complex_budget_question_activates_no_calculation_policy(self):
        decision = self.scope.classify(
            "هزینه دقیق ده شب هتل را حساب کن",
            self.entities,
        )
        self.assertTrue(decision.calculation_limited)
        self.assertIn("محاسبه", decision.guidance)

        numeric = self.scope.classify(
            "هزینه اقامت ۵ نفر برای ۱۰ شب چقدر است؟",
            self.entities,
        )
        self.assertTrue(numeric.calculation_limited)

    def test_closed_world_matrix_marks_missing_services_as_unavailable(self):
        context = self.scope.closed_world_context("هتل صدف ناهار دارد؟")
        self.assertIn("ناهار: ارائه نمی‌شود", context)
        self.assertIn("صبحانه: ارائه می‌شود", context)

    def test_non_matrix_attribute_is_not_assumed_unavailable(self):
        context = self.scope.closed_world_context("هتل صدف استخر دارد؟")
        self.assertNotIn("استخر", context)
        self.assertIn("خارج از این فهرست", context)


if __name__ == "__main__":
    unittest.main()

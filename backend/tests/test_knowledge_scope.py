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
        self.assertEqual(decision.request_level, "single_fact")

    def test_far_topic_is_closed_without_retrieval(self):
        decision = self.scope.classify("آیا جزیره بورس ارز دیجیتال دارد؟", self.entities)
        self.assertEqual(decision.classification, "outside_world")
        self.assertEqual(decision.request_level, "unsupported")

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
        self.assertEqual(numeric.request_level, "calculation_limited")

    def test_broad_dump_is_intercepted_without_retrieval(self):
        decision = self.scope.classify(
            "هر چیزی که درباره جزیره می دانی با تمام جزئیات بگو",
            self.entities,
        )
        self.assertEqual(decision.request_level, "broad_clarification")
        self.assertEqual(decision.retrieval_limit, 0)
        self.assertIn("موضوع مشخص", self.scope.direct_response(decision))

    def test_category_overview_uses_structured_minimal_evidence(self):
        decision = self.scope.classify("گزینه های اقامت چیست؟", self.entities)
        projected = self.scope.project_evidence([], decision)
        self.assertEqual(decision.request_level, "category_overview")
        self.assertIn("هتل صدف", projected)
        self.assertIn("اردوگاه چشمه", projected)
        self.assertNotIn("یورو", projected)
        self.assertNotIn("بیعانه", projected)
        self.assertTrue(self.scope.answer_passes_contract(projected, decision))
        self.assertFalse(
            self.scope.answer_passes_contract(
                projected + "\nقیمت هتل ۲۴۰ یورو است.", decision
            )
        )

    def test_accommodation_calculation_hides_generic_seasonal_cost_chunks(self):
        decision = self.scope.classify(
            "هزینه اقامت ده شب در اردیبهشت را حساب کن", self.entities
        )
        seasonal = type(
            "Result", (), {"topic": "travel_cost", "chunk_id": "season", "text": "۱۰ درصد"}
        )()
        lodging = type(
            "Result", (), {"topic": "accommodation_profile", "chunk_id": "hotel", "text": "قیمت پایه"}
        )()
        projected = self.scope.project_evidence([seasonal, lodging], decision)
        self.assertNotIn("۱۰ درصد", projected)
        self.assertIn("قیمت پایه", projected)

    def test_request_levels_choose_different_contracts(self):
        fact = self.scope.classify("هتل صدف صبحانه دارد؟", self.entities)
        entity = self.scope.classify(
            "قیمت و ظرفیت و امکانات هتل صدف چیست؟", self.entities
        )
        comparison = self.scope.classify(
            "هتل صدف و مهمان خانه موج را مقایسه کن", self.entities
        )
        self.assertEqual(fact.request_level, "single_fact")
        self.assertEqual(entity.request_level, "single_entity")
        self.assertEqual(comparison.request_level, "comparison")
        self.assertLess(fact.retrieval_limit, comparison.retrieval_limit)

    def test_history_resolves_followup_but_does_not_inflate_level(self):
        decision = self.scope.classify(
            "صبحانه چطور؟",
            self.entities,
            contextual_query="هتل صدف چه امکاناتی دارد؟ صبحانه چطور؟",
        )
        self.assertEqual(decision.request_level, "single_fact")
        self.assertIn("هتل صدف", decision.entity_ids)

    def test_calculation_contract_rejects_derived_totals(self):
        decision = self.scope.classify(
            "هزینه پنج نفر برای ده شب را حساب کن", self.entities
        )
        self.assertFalse(
            self.scope.answer_passes_contract(
                "۲۴۰ × ۱۰ = ۲۴۰۰ یورو خواهد بود.", decision
            )
        )
        self.assertTrue(
            self.scope.answer_passes_contract(
                "قیمت پایه هتل صدف شبی ۲۴۰ یورو است.", decision
            )
        )

    def test_closed_world_matrix_marks_missing_services_as_unavailable(self):
        decision = self.scope.classify("هتل صدف ناهار دارد؟", self.entities)
        context = self.scope.closed_world_context("هتل صدف ناهار دارد؟", decision)
        self.assertIn("ناهار: ارائه نمی‌شود", context)
        self.assertIn("صبحانه: ارائه می‌شود", context)
        self.assertNotIn("حمام اختصاصی", context)

    def test_food_matrix_preserves_paid_optional_breakfast(self):
        decision = self.scope.classify("در کدام اقامتگاه غذا سرو می شود؟", self.entities)
        context = self.scope.closed_world_context(
            "در کدام اقامتگاه غذا سرو می شود؟", decision
        )
        self.assertIn("کلبه های نارون", context)
        self.assertIn("صبحانه: با سفارش و هزینه جداگانه", context)

    def test_restaurant_overview_is_structured_and_minimal(self):
        decision = self.scope.classify("چه غذاخوری هایی در جزیره وجود دارد؟", self.entities)
        overview = self.scope.category_overview_response(decision)
        self.assertEqual(decision.request_level, "category_overview")
        self.assertIn("لنگر آبی", overview)
        self.assertIn("تالار خوراک بندر", overview)
        self.assertNotIn("حساسیت", overview)

    def test_restaurant_closed_world_distinguishes_absent_from_unknown(self):
        decision = self.scope.classify("آشپزخانه باران غذای وگان دارد؟", self.entities)
        context = self.scope.closed_world_context(
            "آشپزخانه باران غذای وگان دارد؟", decision
        )
        self.assertIn("گزینه وگان ثابت: وضعیت آن ثابت یا مشخص نیست", context)
        self.assertNotIn("گزینه وگان ثابت: ارائه نمی‌شود", context)

        seafood = self.scope.closed_world_context("باغ مزه غذای دریایی دارد؟")
        self.assertIn("غذای دریایی: ارائه نمی‌شود", seafood)

    def test_known_gap_blocks_tropical_climate_inference(self):
        constraint = self.scope.knowledge_constraints(
            "آیا اقلیم جزیره گرمسیری است؟"
        )
        self.assertIn("طبقه‌بندی رسمی اقلیم", constraint)
        self.assertIn("کافی نیست", constraint)

    def test_culture_overview_is_deterministic_and_relevant(self):
        decision = self.scope.classify(
            "برای شناخت تعامل محترمانه چه موضوع هایی مهم اند؟", self.entities
        )
        overview = self.scope.category_overview_response(decision)
        self.assertIn("حریم خصوصی", overview)
        self.assertIn("احترام به آب", overview)
        self.assertNotIn("موزه فانوس", overview)

    def test_specific_culture_questions_are_single_facts(self):
        for query in (
            "مردم جزیره در بدو دیدار چگونه برخورد می کنند؟",
            "دین مردم جزیره چیست؟",
            "در سلام و احوالپرسی دست دادن یا تعظیم دارند؟",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    self.scope.classify(query, self.entities).request_level,
                    "single_fact",
                )

    def test_related_topics_do_not_make_one_question_multi_part(self):
        decision = self.scope.classify(
            "در کدام اقامتگاه غذا سرو می شود؟", self.entities
        )
        self.assertEqual(decision.request_level, "single_fact")

    def test_non_matrix_attribute_is_not_assumed_unavailable(self):
        context = self.scope.closed_world_context("هتل صدف استخر دارد؟")
        self.assertNotIn("استخر", context)
        self.assertIn("خارج از این فهرست", context)


if __name__ == "__main__":
    unittest.main()

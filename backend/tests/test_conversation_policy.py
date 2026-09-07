import unittest

from sepid_rag.graph import (
    clarification_for_incomplete_query,
    extract_evidence_decision,
    extract_verified_answer,
)
from sepid_rag.prompts import (
    EVIDENCE_JUDGE_PROMPT,
    EVIDENCE_JUDGE_PROMPT_VERSION,
    QUERY_RESOLVER_PROMPT,
    QUERY_RESOLVER_PROMPT_VERSION,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_VERSION,
    VERIFIER_PROMPT,
    VERIFIER_PROMPT_VERSION,
)
from sepid_rag.task_contexts import (
    TASK_CONTEXT_VERSION,
    classify_task_relevance,
    format_task_context,
    task_reminder,
)


class ConversationPolicyTests(unittest.TestCase):
    def test_plainly_incomplete_query_requests_clarification(self):
        self.assertEqual(
            clarification_for_incomplete_query("برای اقامت با"),
            "منظورتان را کمی کامل‌تر می‌کنید؟",
        )

    def test_complete_short_question_is_not_intercepted(self):
        self.assertIsNone(clarification_for_incomplete_query("هتل صدف کجاست؟"))

    def test_empty_message_requests_clarification(self):
        self.assertEqual(
            clarification_for_incomplete_query("   "),
            "لطفاً پرسش خود را کمی کامل‌تر بنویسید.",
        )

    def test_prompt_freezes_grounding_and_progressive_disclosure_rules(self):
        self.assertEqual(SYSTEM_PROMPT_VERSION, "sepid-fa-rag-v14.2-no-entity-guard")
        self.assertIn("حداکثر سه تا پنج محور", SYSTEM_PROMPT)
        self.assertIn("یک حکم کلی را به مصداق خاص منتقل نکنید", SYSTEM_PROMPT)
        self.assertIn("هر ادعای پشتیبانی‌نشده را حذف", SYSTEM_PROMPT)
        self.assertIn("پاسخ را با پیشنهاد ادامه", SYSTEM_PROMPT)
        self.assertIn("قرارداد پاسخ", SYSTEM_PROMPT)

    def test_query_resolver_uses_history_as_intent_not_evidence(self):
        self.assertEqual(QUERY_RESOLVER_PROMPT_VERSION, "sepid-fa-query-resolver-v2-user-intent")
        self.assertIn("فقط پیام‌های قبلی کاربر", QUERY_RESOLVER_PROMPT)
        self.assertIn("retrieval_queries", QUERY_RESOLVER_PROMPT)

    def test_each_research_task_has_problem_objective_and_neutral_boundaries(self):
        self.assertEqual(TASK_CONTEXT_VERSION, "sepid-swts-task-context-v1")
        for task_id in ("task_1", "task_2", "task_3"):
            context = format_task_context(task_id)
            self.assertIn("مسئله:", context)
            self.assertIn("هدف:", context)
            self.assertIn("دامنه اصلی:", context)
            self.assertIn("اطلاعات را پنهان نکنید", context)
            self.assertIn("سؤال بعدی مشخص پیشنهاد نکنید", context)

    def test_free_chat_has_full_corpus_without_research_task_boundary(self):
        context = format_task_context("free_chat")
        self.assertIn("همه موضوع‌های موجود", context)
        self.assertIn("هیچ هدف فعالیتی", context)
        self.assertNotIn("سیاست مرزبندی", context)

    def test_task_topic_relevance_is_deterministic(self):
        self.assertEqual(
            classify_task_relevance("task_2", ("travel_periods",)),
            "core",
        )
        self.assertEqual(
            classify_task_relevance("task_2", ("transport_access",)),
            "adjacent",
        )
        self.assertEqual(
            classify_task_relevance("task_2", ("society_governance",)),
            "outside_task",
        )
        self.assertEqual(
            classify_task_relevance("free_chat", ("society_governance",)),
            "free_chat",
        )
        self.assertIn("مقایسه زمان‌های سفر", task_reminder("task_2"))

    def test_verifier_checks_grounding_math_scope_and_answer_length(self):
        self.assertEqual(VERIFIER_PROMPT_VERSION, "sepid-fa-verifier-v6-closed-evidence")
        self.assertIn("هر واقعیت، عدد، قیمت، درصد", VERIFIER_PROMPT)
        self.assertIn("خود محاسبه درست باشد", VERIFIER_PROMPT)
        self.assertIn("اطلاعات درخواست‌نشده", VERIFIER_PROMPT)
        self.assertIn("سیاست مرزبندی فعالیت", VERIFIER_PROMPT)
        self.assertIn("سطح درخواست", VERIFIER_PROMPT)

    def test_verified_answer_envelope_is_strictly_extracted(self):
        self.assertEqual(
            extract_verified_answer("<verified_answer>پاسخ اصلاح‌شده</verified_answer>"),
            "پاسخ اصلاح‌شده",
        )
        self.assertIsNone(extract_verified_answer("پاسخ بدون برچسب"))

    def test_post_retrieval_judge_envelope_is_strictly_extracted(self):
        self.assertEqual(EVIDENCE_JUDGE_PROMPT_VERSION, "sepid-fa-evidence-judge-v2-coverage")
        self.assertIn("پس از بازیابی", EVIDENCE_JUDGE_PROMPT)
        parsed = extract_evidence_decision(
            '<evidence_decision>{"classification":"supported",'
            '"request_level":"single_fact","selected_chunk_ids":["A"],'
            '"coverage_items":[{"question_part":"پرسش","status":"direct",'
            '"selected_chunk_ids":["A"]}]}</evidence_decision>'
        )
        self.assertEqual(parsed["selected_chunk_ids"], ["A"])
        self.assertIsNone(extract_evidence_decision("not-json"))


if __name__ == "__main__":
    unittest.main()

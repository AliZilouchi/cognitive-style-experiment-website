import unittest

from sepid_rag.graph import clarification_for_incomplete_query
from sepid_rag.prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_VERSION


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
        self.assertEqual(SYSTEM_PROMPT_VERSION, "sepid-fa-rag-v7-grounded-conversation")
        self.assertIn("حداکثر سه تا پنج محور", SYSTEM_PROMPT)
        self.assertIn("یک حکم کلی را به مصداق خاص منتقل نکنید", SYSTEM_PROMPT)
        self.assertIn("هر ادعای پشتیبانی‌نشده را حذف", SYSTEM_PROMPT)
        self.assertIn("پاسخ را با پیشنهاد ادامه", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()

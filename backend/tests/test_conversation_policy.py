import unittest

from sepid_rag.graph import clarification_for_incomplete_query


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


if __name__ == "__main__":
    unittest.main()

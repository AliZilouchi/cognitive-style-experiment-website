import unittest

from sepid_rag.normalization import normalize_persian


class NormalizationTests(unittest.TestCase):
    def test_arabic_variants_digits_and_spacing(self):
        self.assertEqual(normalize_persian("  جزيره\u200cي  سفيد 123  "), "جزیره ی سفید ۱۲۳")


if __name__ == "__main__":
    unittest.main()


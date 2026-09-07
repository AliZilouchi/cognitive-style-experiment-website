import os
import unittest
from unittest.mock import patch

from sepid_rag.config import Settings


class ConfigTests(unittest.TestCase):
    def test_hosted_avalai_configuration_is_accepted(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "experiment",
                "EMBEDDING_PROVIDER": "avalai",
                "EMBEDDING_MODEL": "text-embedding-3-large",
                "EMBEDDING_REVISION": "avalai-2026-09-04",
                "EMBEDDING_DIMENSION": "1024",
                "QUERY_PREFIX": "",
                "DOCUMENT_PREFIX": "",
                "TOP_K": "3",
                "LLM_PROVIDER": "avalai",
                "LLM_MODEL": "gpt-4.1-mini-2025-04-14",
                "AVALAI_API_KEY": "test-avalai-key",
                "AVALAI_BASE_URL": "https://api.avalai.ir/v1",
                "API_SHARED_SECRET": "test-secret-with-at-least-thirty-two-characters",
            },
            clear=True,
        ):
            settings = Settings.from_env()
            self.assertEqual(settings.embedding_provider, "avalai")
            self.assertEqual(settings.llm_provider, "avalai")
            self.assertEqual(settings.embedding_dimension, 1024)
            self.assertEqual(settings.avalai_base_url, "https://api.avalai.ir/v1")
            self.assertTrue(settings.enable_response_verifier)
            self.assertEqual(settings.resolver_model, "")
            self.assertEqual(settings.resolver_max_tokens, 250)
            self.assertEqual(settings.resolver_timeout_seconds, 8)

    def test_resolver_can_use_a_separate_fast_model(self):
        with patch.dict(
            os.environ,
            {
                "RESOLVER_MODEL": "fast-resolver-model",
                "RESOLVER_MAX_TOKENS": "180",
                "RESOLVER_TIMEOUT_SECONDS": "4.5",
            },
            clear=True,
        ):
            settings = Settings.from_env()
            self.assertEqual(settings.resolver_model, "fast-resolver-model")
            self.assertEqual(settings.resolver_max_tokens, 180)
            self.assertEqual(settings.resolver_timeout_seconds, 4.5)

    def test_response_verifier_can_be_disabled_for_diagnostics(self):
        with patch.dict(
            os.environ,
            {"ENABLE_RESPONSE_VERIFIER": "false"},
            clear=True,
        ):
            settings = Settings.from_env()
            self.assertFalse(settings.enable_response_verifier)

    def test_hosted_openrouter_configuration_is_accepted(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "experiment",
                "EMBEDDING_PROVIDER": "openrouter",
                "EMBEDDING_MODEL": "intfloat/multilingual-e5-large",
                "EMBEDDING_REVISION": "openrouter-catalog-2026-08-25",
                "EMBEDDING_DIMENSION": "1024",
                # Vercel commonly trims the trailing spaces from these values.
                "QUERY_PREFIX": "query:",
                "DOCUMENT_PREFIX": "passage:",
                "TOP_K": "5",
                "LLM_PROVIDER": "openrouter",
                "LLM_MODEL": "openai/gpt-4o-mini",
                "OPENROUTER_API_KEY": "test-openrouter-key",
                "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
                "API_SHARED_SECRET": "test-secret-with-at-least-thirty-two-characters",
            },
            clear=True,
        ):
            settings = Settings.from_env()
            self.assertEqual(settings.embedding_provider, "openrouter")
            self.assertEqual(settings.llm_provider, "openrouter")
            self.assertEqual(settings.embedding_dimension, 1024)
            self.assertEqual(settings.query_prefix, "query: ")
            self.assertEqual(settings.document_prefix, "passage: ")

    def test_openrouter_requires_its_api_key(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "evaluation",
                "EMBEDDING_PROVIDER": "openrouter",
                "EMBEDDING_MODEL": "intfloat/multilingual-e5-large",
                "EMBEDDING_REVISION": "freeze-date",
                "QUERY_PREFIX": "query: ",
                "DOCUMENT_PREFIX": "passage: ",
                "OPENROUTER_API_KEY": "",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "OPENROUTER_API_KEY"):
                Settings.from_env()

    def test_hosted_together_configuration_decodes_prefix_and_is_accepted(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "experiment",
                "EMBEDDING_PROVIDER": "together",
                "EMBEDDING_MODEL": "intfloat/multilingual-e5-large-instruct",
                "EMBEDDING_REVISION": "together-serverless-catalog-2026-08-25",
                "EMBEDDING_DIMENSION": "1024",
                "QUERY_PREFIX": "Instruct: retrieve Persian passages\\nQuery: ",
                "DOCUMENT_PREFIX": "",
                "TOP_K": "5",
                "LLM_PROVIDER": "groq",
                "LLM_MODEL": "qwen/qwen3.6-27b",
                "GROQ_API_KEY": "test-groq-key",
                "TOGETHER_API_KEY": "test-together-key",
                "API_SHARED_SECRET": "test-secret-with-at-least-thirty-two-characters",
            },
            clear=True,
        ):
            settings = Settings.from_env()
            self.assertEqual(settings.embedding_provider, "together")
            self.assertEqual(settings.embedding_dimension, 1024)
            self.assertIn("\nQuery: ", settings.query_prefix)

    def test_experiment_requires_shared_api_secret(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "experiment",
                "EMBEDDING_PROVIDER": "sentence_transformers",
                "EMBEDDING_MODEL": "example/model",
                "EMBEDDING_REVISION": "0123456789abcdef",
                "TOP_K": "5",
                "LLM_PROVIDER": "groq",
                "LLM_MODEL": "example-chat-model",
                "GROQ_API_KEY": "test-key",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "API_SHARED_SECRET"):
                Settings.from_env()

    def test_experiment_rejects_development_providers(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "experiment",
                "EMBEDDING_PROVIDER": "hashing",
                "LLM_PROVIDER": "echo",
                "TOP_K": "5",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "forbidden"):
                Settings.from_env()

    def test_experiment_groq_requires_its_key_not_together_key(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "experiment",
                "EMBEDDING_PROVIDER": "sentence_transformers",
                "EMBEDDING_MODEL": "example/model",
                "EMBEDDING_REVISION": "0123456789abcdef",
                "TOP_K": "5",
                "LLM_PROVIDER": "groq",
                "LLM_MODEL": "example-chat-model",
                "GROQ_API_KEY": "",
                "API_SHARED_SECRET": "test-secret-with-at-least-thirty-two-characters",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "GROQ_API_KEY"):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()

"""Environment configuration with strict experiment-mode validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is present in deployed builds
    load_dotenv = None


PACKAGE_PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = (
    Path.cwd()
    if (Path.cwd() / "corpus" / "corpus_manifest.json").is_file()
    else PACKAGE_PROJECT_ROOT
)

if load_dotenv is not None:
    # Makes the exact same backend configuration usable from Windows, Docker,
    # and Vercel. Real process/Vercel variables always win over the local file.
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _prefix(name: str) -> str:
    """Decode escapes and preserve the separator required by E5 prefixes."""
    value = os.getenv(name, "").replace("\\n", "\n").replace("\\t", "\t")
    # Deployment dashboards may trim trailing spaces from `query: ` and
    # `passage: `. Accept the trimmed forms without changing the model input.
    if value in {"query:", "passage:"}:
        value += " "
    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    corpus_root: Path
    index_dir: Path
    embedding_provider: str
    embedding_model: str
    embedding_revision: str
    embedding_dimension: int
    query_prefix: str
    document_prefix: str
    top_k: int
    retrieval_score_margin: float
    max_chunks_per_source: int
    mmr_lambda: float
    llm_provider: str
    llm_model: str
    llm_max_tokens: int
    together_api_key: str
    groq_api_key: str
    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_http_referer: str
    openrouter_app_title: str
    avalai_api_key: str
    avalai_base_url: str
    api_shared_secret: str
    enable_debug_retrieval: bool

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            app_env=os.getenv("APP_ENV", "development").strip().lower(),
            corpus_root=Path(os.getenv("CORPUS_ROOT", PROJECT_ROOT / "corpus")).resolve(),
            index_dir=Path(os.getenv("INDEX_DIR", PROJECT_ROOT / "data/index")).resolve(),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "hashing").strip().lower(),
            embedding_model=os.getenv("EMBEDDING_MODEL", "development-only").strip(),
            embedding_revision=os.getenv("EMBEDDING_REVISION", "development-only").strip(),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "768")),
            query_prefix=_prefix("QUERY_PREFIX"),
            document_prefix=_prefix("DOCUMENT_PREFIX"),
            top_k=int(os.getenv("TOP_K", "3")),
            retrieval_score_margin=float(os.getenv("RETRIEVAL_SCORE_MARGIN", "0.12")),
            max_chunks_per_source=int(os.getenv("MAX_CHUNKS_PER_SOURCE", "2")),
            mmr_lambda=float(os.getenv("MMR_LAMBDA", "0.75")),
            llm_provider=os.getenv("LLM_PROVIDER", "echo").strip().lower(),
            llm_model=os.getenv("LLM_MODEL", "development-only").strip(),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "700")),
            together_api_key=os.getenv("TOGETHER_API_KEY", "").strip(),
            groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
            openrouter_base_url=os.getenv(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ).strip().rstrip("/"),
            openrouter_http_referer=os.getenv("OPENROUTER_HTTP_REFERER", "").strip(),
            openrouter_app_title=os.getenv(
                "OPENROUTER_APP_TITLE", "Cognitive Style Experiment"
            ).strip(),
            avalai_api_key=os.getenv("AVALAI_API_KEY", "").strip(),
            avalai_base_url=os.getenv(
                "AVALAI_BASE_URL", "https://api.avalai.ir/v1"
            ).strip().rstrip("/"),
            api_shared_secret=os.getenv("API_SHARED_SECRET", "").strip(),
            enable_debug_retrieval=_bool("ENABLE_DEBUG_RETRIEVAL", True),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.app_env not in {"development", "test", "evaluation", "experiment"}:
            raise ValueError("APP_ENV must be development, test, evaluation, or experiment")
        if self.top_k < 1:
            raise ValueError("TOP_K must be a positive integer")
        if self.top_k > 10:
            raise ValueError("TOP_K cannot exceed 10 semantic chunks")
        if not 0 <= self.retrieval_score_margin <= 2:
            raise ValueError("RETRIEVAL_SCORE_MARGIN must be between 0 and 2")
        if self.max_chunks_per_source < 1:
            raise ValueError("MAX_CHUNKS_PER_SOURCE must be positive")
        if not 0 <= self.mmr_lambda <= 1:
            raise ValueError("MMR_LAMBDA must be between 0 and 1")
        if self.embedding_dimension < 8:
            raise ValueError("EMBEDDING_DIMENSION is implausibly small")
        if self.llm_max_tokens < 1:
            raise ValueError("LLM_MAX_TOKENS must be a positive integer")
        if self.embedding_provider not in {
            "hashing",
            "sentence_transformers",
            "together",
            "openrouter",
            "avalai",
        }:
            raise ValueError("Unsupported EMBEDDING_PROVIDER")
        if self.llm_provider not in {"echo", "together", "groq", "openrouter", "avalai"}:
            raise ValueError("Unsupported LLM_PROVIDER")

        if self.app_env in {"evaluation", "experiment"}:
            if self.embedding_provider == "hashing":
                raise ValueError("Hash embeddings are forbidden in evaluation/experiment mode")
            values = {
                "EMBEDDING_MODEL": self.embedding_model,
                "EMBEDDING_REVISION": self.embedding_revision,
                "QUERY_PREFIX": self.query_prefix,
                "DOCUMENT_PREFIX": self.document_prefix,
            }
            placeholders = [name for name, value in values.items() if "REPLACE_" in value]
            if placeholders:
                raise ValueError(f"Embedding configuration has placeholders: {placeholders}")
            if self.embedding_provider == "together" and not self.together_api_key:
                raise ValueError("TOGETHER_API_KEY is required for Together embeddings")
            if self.embedding_provider == "openrouter" and (
                not self.openrouter_api_key or "REPLACE_" in self.openrouter_api_key
            ):
                raise ValueError("OPENROUTER_API_KEY is required for OpenRouter embeddings")
            if self.embedding_provider == "avalai" and (
                not self.avalai_api_key or "REPLACE_" in self.avalai_api_key
            ):
                raise ValueError("AVALAI_API_KEY is required for AvalAI embeddings")

        if self.app_env == "experiment":
            if len(self.api_shared_secret) < 32 or "REPLACE_" in self.api_shared_secret:
                raise ValueError(
                    "API_SHARED_SECRET must be a non-placeholder value of at least 32 characters "
                    "in experiment mode"
                )
            if self.llm_provider == "echo":
                raise ValueError("Echo responses are forbidden in experiment mode")
            if "REPLACE_" in self.llm_model:
                raise ValueError("Experiment LLM configuration has a placeholder")
            if self.llm_provider == "together" and (
                "REPLACE_" in self.together_api_key or not self.together_api_key
            ):
                raise ValueError("TOGETHER_API_KEY is required in experiment mode")
            if self.llm_provider == "groq" and (
                "REPLACE_" in self.groq_api_key or not self.groq_api_key
            ):
                raise ValueError("GROQ_API_KEY is required in experiment mode")
            if self.llm_provider == "openrouter" and (
                "REPLACE_" in self.openrouter_api_key or not self.openrouter_api_key
            ):
                raise ValueError("OPENROUTER_API_KEY is required in experiment mode")
            if self.llm_provider == "avalai" and (
                "REPLACE_" in self.avalai_api_key or not self.avalai_api_key
            ):
                raise ValueError("AVALAI_API_KEY is required in experiment mode")
            if (
                self.embedding_provider == "openrouter"
                or self.llm_provider == "openrouter"
            ) and not self.openrouter_base_url.startswith("https://"):
                raise ValueError("OPENROUTER_BASE_URL must use HTTPS in experiment mode")
            if (
                self.embedding_provider == "avalai" or self.llm_provider == "avalai"
            ) and not self.avalai_base_url.startswith("https://"):
                raise ValueError("AVALAI_BASE_URL must use HTTPS in experiment mode")

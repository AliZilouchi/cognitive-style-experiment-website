"""Strict allowlist-based corpus loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .normalization import normalize_persian


@dataclass(frozen=True)
class CorpusDocument:
    source_id: str
    relative_path: str
    text: str
    retrieval_text: str


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_allowlisted_corpus(corpus_root: Path) -> list[CorpusDocument]:
    """Load exactly the ordered manifest/allowlist intersection and nothing else."""

    root = corpus_root.resolve()
    sources_root = (root / "sources").resolve()
    allowlist = _json(root / "ingestion" / "allowlist.json")
    manifest = _json(root / "corpus_manifest.json")

    if allowlist.get("corpus_id") != manifest.get("corpus_id"):
        raise ValueError("Allowlist and manifest corpus_id values differ")

    allowed = [
        (item["source_id"], item["relative_path"])
        for item in allowlist.get("sources", [])
    ]
    declared = [
        (item["source_id"], f"sources/{item['file']}")
        for item in manifest.get("sources", [])
    ]
    if not allowed or allowed != declared:
        raise ValueError("Allowlist must exactly match the ordered manifest")

    seen_ids: set[str] = set()
    seen_paths: set[Path] = set()
    documents: list[CorpusDocument] = []
    for source_id, relative_path in allowed:
        candidate = root / relative_path
        resolved = candidate.resolve()
        if source_id in seen_ids or resolved in seen_paths:
            raise ValueError(f"Duplicate corpus entry: {source_id}")
        if candidate.is_symlink() or resolved.parent != sources_root:
            raise ValueError(f"Unsafe corpus source path: {relative_path}")
        if resolved.suffix.lower() != ".md" or not resolved.is_file():
            raise ValueError(f"Invalid allowlisted source: {relative_path}")
        text = resolved.read_text(encoding="utf-8")
        documents.append(
            CorpusDocument(
                source_id=source_id,
                relative_path=relative_path,
                text=text,
                retrieval_text=normalize_persian(text),
            )
        )
        seen_ids.add(source_id)
        seen_paths.add(resolved)

    if len(documents) != manifest.get("source_count"):
        raise ValueError("Loaded source count does not match manifest")
    return documents


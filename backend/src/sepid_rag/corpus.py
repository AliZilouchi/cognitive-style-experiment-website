"""Strict allowlist-based corpus loading with semantic Markdown chunks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .normalization import normalize_persian


@dataclass(frozen=True)
class CorpusDocument:
    source_id: str
    chunk_id: str
    task_ids: tuple[str, ...]
    topic: str
    relative_path: str
    text: str
    retrieval_text: str


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _task_ids(source_id: str) -> tuple[str, ...]:
    number = int(source_id[1:])
    if number == 1:
        return ("task_1", "task_2")
    if 2 <= number <= 4:
        return ("task_1",)
    if 5 <= number <= 10:
        return ("task_2",)
    return ("task_3",)


def _semantic_chunks(
    source_id: str,
    relative_path: str,
    topic: str,
    markdown: str,
) -> list[CorpusDocument]:
    """Split on Markdown headings and paragraphs without overlapping facts."""

    title = ""
    section = ""
    chunks: list[CorpusDocument] = []
    blocks = [block.strip() for block in re.split(r"\n\s*\n", markdown) if block.strip()]

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and all(line.startswith("#") for line in lines):
            for line in lines:
                heading = line.lstrip("#").strip()
                if line.startswith("##"):
                    section = heading
                else:
                    title = heading
                    section = ""
            continue

        heading_context = [value for value in (title, section) if value]
        contextual_text = "\n".join([*heading_context, block])
        chunk_id = f"{source_id}-C{len(chunks) + 1:02d}"
        chunks.append(
            CorpusDocument(
                source_id=source_id,
                chunk_id=chunk_id,
                task_ids=_task_ids(source_id),
                topic=topic,
                relative_path=relative_path,
                text=contextual_text,
                retrieval_text=normalize_persian(contextual_text),
            )
        )

    if not chunks:
        raise ValueError(f"Corpus source contains no semantic chunks: {relative_path}")
    return chunks


def load_allowlisted_corpus(corpus_root: Path) -> list[CorpusDocument]:
    """Load and semantically chunk exactly the allowlisted sources."""

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
    manifest_sources = manifest.get("sources", [])
    declared = [(item["source_id"], f"sources/{item['file']}") for item in manifest_sources]
    topics = {item["source_id"]: item["topic"] for item in manifest_sources}
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
        markdown = resolved.read_text(encoding="utf-8")
        documents.extend(
            _semantic_chunks(
                source_id=source_id,
                relative_path=relative_path,
                topic=topics[source_id],
                markdown=markdown,
            )
        )
        seen_ids.add(source_id)
        seen_paths.add(resolved)

    if len(seen_ids) != manifest.get("source_count"):
        raise ValueError("Loaded source count does not match manifest")
    return documents

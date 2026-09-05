"""Strict loader for the hybrid, provenance-linked corpus."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .normalization import normalize_persian


@dataclass(frozen=True)
class CorpusDocument:
    source_id: str
    source_ids: tuple[str, ...]
    chunk_id: str
    task_ids: tuple[str, ...]
    node_type: str
    topic: str
    entities: tuple[str, ...]
    coverage_terms: tuple[str, ...]
    parent_ids: tuple[str, ...]
    relative_path: str
    text: str
    retrieval_text: str


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_allowlisted_corpus(corpus_root: Path) -> list[CorpusDocument]:
    """Validate originals and load curated units plus original-source fallbacks."""

    root = corpus_root.resolve()
    sources_root = (root / "sources").resolve()
    enriched_root = (root / "enriched").resolve()
    allowed_source_roots = {sources_root, enriched_root}
    allowlist = _json(root / "ingestion" / "allowlist.json")
    manifest = _json(root / "corpus_manifest.json")
    curated = _json(root / "curated" / "chunks.json")

    if allowlist.get("corpus_id") != manifest.get("corpus_id"):
        raise ValueError("Allowlist and manifest corpus_id values differ")
    if curated.get("source_corpus_id") != manifest.get("corpus_id"):
        raise ValueError("Curated corpus does not identify the source corpus")

    allowed = [
        (item["source_id"], item["relative_path"])
        for item in allowlist.get("sources", [])
    ]
    manifest_sources = manifest.get("sources", [])
    declared = [
        (
            item["source_id"],
            item.get("relative_path", f"sources/{item.get('file', '')}"),
        )
        for item in manifest_sources
    ]
    if not allowed or allowed != declared:
        raise ValueError("Allowlist must exactly match the ordered manifest")

    source_paths: dict[str, str] = {}
    source_texts: dict[str, str] = {}
    seen_paths: set[Path] = set()
    for source_id, relative_path in allowed:
        resolved = (root / relative_path).resolve()
        if source_id in source_paths or resolved in seen_paths:
            raise ValueError(f"Duplicate corpus entry: {source_id}")
        if resolved.is_symlink() or resolved.parent not in allowed_source_roots:
            raise ValueError(f"Unsafe corpus source path: {relative_path}")
        if resolved.suffix.lower() != ".md" or not resolved.is_file():
            raise ValueError(f"Invalid allowlisted source: {relative_path}")
        source_paths[source_id] = relative_path
        source_texts[source_id] = resolved.read_text(encoding="utf-8").strip()
        seen_paths.add(resolved)

    if len(source_paths) != manifest.get("source_count"):
        raise ValueError("Loaded source count does not match manifest")

    rows = curated.get("chunks", [])
    if len(rows) != curated.get("chunk_count") or not rows:
        raise ValueError("Curated chunk count does not match its manifest")
    chunk_ids = {row.get("chunk_id") for row in rows}
    if None in chunk_ids or len(chunk_ids) != len(rows):
        raise ValueError("Curated chunk IDs must be present and unique")

    documents: list[CorpusDocument] = []
    valid_tasks = {"task_1", "task_2", "task_3"}
    valid_node_types = {"index", "fact", "comparison", "source"}
    for row in rows:
        source_ids = tuple(row.get("source_ids", []))
        task_ids = tuple(row.get("task_ids", []))
        parent_ids = tuple(row.get("parent_ids", []))
        entities = tuple(row.get("entities", []))
        coverage_terms = tuple(row.get("coverage_terms", []))
        node_type = row.get("node_type", "")
        text_value = str(row.get("text", "")).strip()

        if not source_ids or any(source_id not in source_paths for source_id in source_ids):
            raise ValueError(f"Unknown provenance in chunk {row['chunk_id']}")
        if not task_ids or not set(task_ids).issubset(valid_tasks):
            raise ValueError(f"Invalid task scope in chunk {row['chunk_id']}")
        if node_type not in valid_node_types:
            raise ValueError(f"Invalid node type in chunk {row['chunk_id']}")
        if any(parent_id not in chunk_ids for parent_id in parent_ids):
            raise ValueError(f"Unknown parent in chunk {row['chunk_id']}")
        if not text_value:
            raise ValueError(f"Empty curated chunk {row['chunk_id']}")

        retrieval_text = "\n".join(
            part
            for part in (
                f"موضوع: {row.get('topic', '')}",
                f"موجودیت‌ها: {'، '.join(entities)}" if entities else "",
                text_value,
            )
            if part
        )
        documents.append(
            CorpusDocument(
                source_id=source_ids[0],
                source_ids=source_ids,
                chunk_id=row["chunk_id"],
                task_ids=task_ids,
                node_type=node_type,
                topic=row.get("topic", ""),
                entities=entities,
                coverage_terms=coverage_terms,
                parent_ids=parent_ids,
                relative_path=f"curated/chunks.json#{row['chunk_id']}",
                text=text_value,
                retrieval_text=normalize_persian(retrieval_text),
            )
        )

    # The curated layer is optimized for predictable overview, fact, and
    # comparison questions.  The complete allowlisted source layer remains
    # searchable as a fallback for unusual wording and details that a curated
    # summary may omit.  Originals are deliberately not rewritten here.
    source_tasks: dict[str, tuple[str, ...]] = {
        "S01": ("task_1", "task_2"),
        **{f"S{i:02d}": ("task_1",) for i in range(2, 5)},
        **{f"S{i:02d}": ("task_2",) for i in range(5, 11)},
        **{f"S{i:02d}": ("task_3",) for i in range(11, 19)},
        "E01": ("task_1", "task_2", "task_3"),
        "E02": ("task_3",),
        "E03": ("task_3",),
        "E04": ("task_3",),
        "E05": ("task_2", "task_3"),
        "E06": ("task_2",),
        "E07": ("task_1",),
        "E08": ("task_2", "task_3"),
        "E09": ("task_2",),
        "E10": ("task_1", "task_2", "task_3"),
        "E11": ("task_3",),
        "E12": ("task_1", "task_2", "task_3"),
    }
    for source_id, relative_path in allowed:
        text_value = source_texts[source_id]
        documents.append(
            CorpusDocument(
                source_id=source_id,
                source_ids=(source_id,),
                chunk_id=f"{source_id}-SOURCE-FALLBACK",
                task_ids=source_tasks[source_id],
                node_type="source",
                topic="original_source",
                entities=(),
                coverage_terms=(),
                parent_ids=(),
                relative_path=relative_path,
                text=text_value,
                retrieval_text=normalize_persian(text_value),
            )
        )
    return documents

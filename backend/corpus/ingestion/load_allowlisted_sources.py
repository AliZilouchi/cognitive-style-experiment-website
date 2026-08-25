#!/usr/bin/env python3
"""Load only explicitly allowlisted Sepid Island RAG sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class SourceRecord(TypedDict):
    source_id: str
    path: str
    text: str


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = PACKAGE_ROOT / "ingestion" / "allowlist.json"
MANIFEST_PATH = PACKAGE_ROOT / "corpus_manifest.json"
SOURCES_ROOT = (PACKAGE_ROOT / "sources").resolve()


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_allowlisted_sources() -> list[SourceRecord]:
    allowlist = _read_json(ALLOWLIST_PATH)
    manifest = _read_json(MANIFEST_PATH)
    entries = allowlist.get("sources", [])

    if allowlist.get("corpus_id") != manifest.get("corpus_id"):
        raise ValueError("Allowlist and manifest corpus_id values differ")
    if not entries:
        raise ValueError("Ingestion allowlist is empty")

    allowed_pairs = [(item["source_id"], item["relative_path"]) for item in entries]
    manifest_pairs = [
        (item["source_id"], f"sources/{item['file']}")
        for item in manifest.get("sources", [])
    ]
    if allowed_pairs != manifest_pairs:
        raise ValueError("Allowlist must exactly match the ordered manifest source set")

    seen_ids: set[str] = set()
    seen_paths: set[Path] = set()
    records: list[SourceRecord] = []

    for source_id, relative_path in allowed_pairs:
        candidate = PACKAGE_ROOT / relative_path
        resolved = candidate.resolve()

        if source_id in seen_ids or resolved in seen_paths:
            raise ValueError(f"Duplicate allowlist entry: {source_id} / {relative_path}")
        if candidate.is_symlink():
            raise ValueError(f"Symlink sources are forbidden: {relative_path}")
        if resolved.parent != SOURCES_ROOT:
            raise ValueError(f"Source must be directly inside sources/: {relative_path}")
        if resolved.suffix.lower() != ".md":
            raise ValueError(f"Only Markdown sources are accepted: {relative_path}")
        if not resolved.is_file():
            raise FileNotFoundError(f"Allowlisted source is missing: {relative_path}")

        seen_ids.add(source_id)
        seen_paths.add(resolved)
        records.append(
            {
                "source_id": source_id,
                "path": relative_path,
                "text": resolved.read_text(encoding="utf-8"),
            }
        )

    return records


if __name__ == "__main__":
    loaded = load_allowlisted_sources()
    print(json.dumps({"status": "ok", "source_count": len(loaded)}, ensure_ascii=False))

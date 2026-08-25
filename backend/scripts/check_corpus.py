#!/usr/bin/env python3
"""Validate that only the 18 explicitly allowlisted sources can be ingested."""

from __future__ import annotations

import json

from sepid_rag.config import Settings
from sepid_rag.corpus import load_allowlisted_corpus


def main() -> int:
    settings = Settings.from_env()
    documents = load_allowlisted_corpus(settings.corpus_root)
    print(
        json.dumps(
            {
                "status": "ok",
                "source_count": len(documents),
                "source_ids": [document.source_id for document in documents],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


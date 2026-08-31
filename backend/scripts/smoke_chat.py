#!/usr/bin/env python3
"""One-command end-to-end retrieval/graph smoke test."""

from __future__ import annotations

import json
import sys

from sepid_rag.service import RagService


def main() -> int:
    query = " ".join(sys.argv[1:]).strip() or "چه گزینه‌هایی برای اقامت وجود دارد؟"
    result = RagService.create().chat(query, "task_1")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

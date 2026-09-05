"""Deterministic world-boundary and closed-world metadata for Sepid Island."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .normalization import normalize_persian


@dataclass(frozen=True)
class ScopeDecision:
    classification: str
    topic_ids: tuple[str, ...]
    calculation_limited: bool
    guidance: str


class KnowledgeScope:
    def __init__(self, data: dict) -> None:
        self.data = data
        self.version = str(data["version"])
        self.outside_world_response = str(data["outside_world_response"])
        self.not_documented_response = str(data["not_documented_response"])
        self._topics = [
            (
                str(item["id"]),
                tuple(normalize_persian(alias) for alias in item.get("aliases", [])),
            )
            for item in data.get("topics", [])
        ]
        self._outside = tuple(
            normalize_persian(item) for item in data.get("outside_world_indicators", [])
        )
        self._calculation = tuple(
            normalize_persian(item) for item in data.get("calculation_indicators", [])
        )

    @classmethod
    def load(cls, corpus_root: Path) -> "KnowledgeScope":
        path = corpus_root / "knowledge_scope.json"
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def classify(self, query_with_context: str, known_entities: set[str]) -> ScopeDecision:
        normalized = normalize_persian(query_with_context)
        topics = tuple(
            topic_id
            for topic_id, aliases in self._topics
            if any(alias in normalized for alias in aliases)
        )
        has_entity = any(
            normalize_persian(entity) in normalized for entity in known_entities
        )
        outside_hits = [item for item in self._outside if item in normalized]
        numeric_tokens = re.findall(r"(?<!\w)[۰-۹]+(?:[٫.]?[۰-۹]+)?(?!\w)", normalized)
        calculation_limited = any(item in normalized for item in self._calculation) or (
            len(numeric_tokens) >= 2 and any(term in normalized for term in ("هزینه", "قیمت", "یورو"))
        )

        # A recognized island topic/entity wins over an incidental outside term.
        # This permits questions such as whether the island has a bank while
        # keeping completely unrelated requests outside the fictional world.
        if topics or has_entity:
            classification = "supported"
        elif outside_hits:
            classification = "outside_world"
        else:
            classification = "unknown_topic"

        guidance = self._format_guidance(classification, topics, calculation_limited)
        return ScopeDecision(classification, topics, calculation_limited, guidance)

    def _format_guidance(
        self,
        classification: str,
        topics: tuple[str, ...],
        calculation_limited: bool,
    ) -> str:
        lines = [
            f"نسخه نمایه دانش: {self.version}",
            f"طبقه‌بندی پوشش: {classification}",
            f"موضوع‌های شناسایی‌شده: {', '.join(topics) if topics else 'هیچ‌کدام'}",
        ]
        if calculation_limited:
            lines.append(f"سیاست محاسبه: {self.data['calculation_policy']}")
        return "\n".join(lines)

    def closed_world_context(self, query_with_context: str) -> str:
        normalized = normalize_persian(query_with_context)
        group = self.data.get("closed_world", {}).get("accommodation_services", {})
        entities = group.get("entities", {})
        accommodation_terms = ("اقامت", "هتل", "مهمان خانه", "خانه مسافر", "کلبه", "اردوگاه")
        mentioned = [
            name for name in entities if normalize_persian(name) in normalized
        ]
        if not mentioned and not any(term in normalized for term in accommodation_terms):
            return ""
        selected = entities if not mentioned else {name: entities[name] for name in mentioned}
        labels = group.get("service_labels", {})
        rows = []
        for name, values in selected.items():
            rendered = []
            for key, value in values.items():
                label = labels.get(key, key)
                status = "ارائه می‌شود" if value is True else "ارائه نمی‌شود" if value is False else "با سفارش و هزینه جداگانه"
                rendered.append(f"{label}: {status}")
            rows.append(f"- {name}: " + "؛ ".join(rendered))
        return "\n".join([str(group.get("rule", "")), *rows])

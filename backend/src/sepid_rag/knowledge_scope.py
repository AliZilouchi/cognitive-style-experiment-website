"""Deterministic knowledge boundary and request-level planner for Sepid Island."""

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
    request_level: str = "single_fact"
    entity_ids: tuple[str, ...] = ()
    requested_fields: tuple[str, ...] = ()
    retrieval_limit: int = 5
    preferred_node_types: tuple[str, ...] = ()
    response_contract: str = ""


class KnowledgeScope:
    def __init__(self, data: dict) -> None:
        self.data = data
        self.version = str(data["version"])
        self.outside_world_response = str(data["outside_world_response"])
        self.not_documented_response = str(data["not_documented_response"])
        self._topics = [
            (str(item["id"]), tuple(normalize_persian(alias) for alias in item.get("aliases", [])))
            for item in data.get("topics", [])
        ]
        self._outside = self._normalized_values(data.get("outside_world_indicators", []))
        self._calculation = self._normalized_values(data.get("calculation_indicators", []))
        planner = data.get("request_planner", {})
        self._broad = self._normalized_values(planner.get("broad_indicators", []))
        self._comparison = self._normalized_values(planner.get("comparison_indicators", []))
        self._overview = self._normalized_values(planner.get("overview_indicators", []))
        self._field_aliases = {
            str(item["id"]): tuple(normalize_persian(alias) for alias in item.get("aliases", []))
            for item in planner.get("fields", [])
        }
        self._non_entity_terms = {
            alias for _, aliases in self._topics for alias in aliases
        } | {alias for aliases in self._field_aliases.values() for alias in aliases}
        self._contracts = planner.get("contracts", {})
        self._category_overviews = planner.get("category_overviews", {})

    @staticmethod
    def _normalized_values(values: list[str]) -> tuple[str, ...]:
        return tuple(normalize_persian(str(value)) for value in values)

    @classmethod
    def load(cls, corpus_root: Path) -> "KnowledgeScope":
        path = corpus_root / "knowledge_scope.json"
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def classify(
        self,
        query: str,
        known_entities: set[str],
        contextual_query: str | None = None,
    ) -> ScopeDecision:
        """Decide coverage, retrieval breadth, and answer shape for this turn."""
        normalized = normalize_persian(query)
        contextual = normalize_persian(contextual_query or query)
        topics = self._matched_topics(normalized)
        if not topics and contextual != normalized:
            topics = self._matched_topics(contextual)
        entities = self._matched_entities(normalized, known_entities)
        if not entities and contextual != normalized:
            entities = self._matched_entities(contextual, known_entities)
        fields = tuple(
            field_id
            for field_id, aliases in self._field_aliases.items()
            if any(alias in normalized for alias in aliases)
        )
        outside_hits = tuple(item for item in self._outside if item in normalized)
        calculation_limited = self._is_calculation_request(normalized)

        # An outside-world phrase can contain a generic supported word (for
        # example «بازار بورس» contains «بازار»). Such substring overlap must
        # not open retrieval unless the turn also names a real entity or field.
        if outside_hits and not entities and not fields:
            classification = "outside_world"
        elif topics or entities or fields:
            classification = "supported"
        elif outside_hits:
            classification = "outside_world"
        else:
            classification = "unknown_topic"

        level = self._request_level(
            normalized, classification, topics, entities, fields, calculation_limited
        )
        contract = dict(self._contracts.get(level, {}))
        guidance = self._format_guidance(
            classification, topics, entities, fields, calculation_limited, level, contract
        )
        return ScopeDecision(
            classification=classification,
            topic_ids=topics,
            calculation_limited=calculation_limited,
            guidance=guidance,
            request_level=level,
            entity_ids=entities,
            requested_fields=fields,
            retrieval_limit=int(contract.get("retrieval_limit", 5)),
            preferred_node_types=tuple(contract.get("preferred_node_types", [])),
            response_contract=str(contract.get("instruction", "")),
        )

    def _matched_topics(self, normalized: str) -> tuple[str, ...]:
        return tuple(
            topic_id for topic_id, aliases in self._topics if any(alias in normalized for alias in aliases)
        )

    def _matched_entities(self, normalized: str, entities: set[str]) -> tuple[str, ...]:
        return tuple(
            sorted(
                entity
                for entity in entities
                if normalize_persian(entity) not in self._non_entity_terms
                and normalize_persian(entity) in normalized
            )
        )

    def _is_calculation_request(self, normalized: str) -> bool:
        numeric_tokens = re.findall(r"(?<!\w)[۰-۹0-9]+(?:[٫.]?[۰-۹0-9]+)?(?!\w)", normalized)
        return any(item in normalized for item in self._calculation) or (
            len(numeric_tokens) >= 2 and any(term in normalized for term in ("هزینه", "قیمت", "یورو"))
        )

    def _request_level(
        self,
        normalized: str,
        classification: str,
        topics: tuple[str, ...],
        entities: tuple[str, ...],
        fields: tuple[str, ...],
        calculation_limited: bool,
    ) -> str:
        if classification != "supported":
            return "unsupported"
        if any(marker in normalized for marker in self._broad):
            return "broad_clarification"
        if calculation_limited:
            return "calculation_limited"
        if any(marker in normalized for marker in self._comparison) or len(entities) > 1:
            return "comparison"
        explicit_parts = normalized.count("؟") + normalized.count("?")
        if len(set(topics) - {"overview"}) > 1 or explicit_parts > 1:
            return "multi_part"
        if len(entities) == 1 and len(fields) > 1:
            return "single_entity"
        if len(entities) == 1 or len(fields) == 1:
            return "single_fact"
        return "category_overview"

    def _format_guidance(
        self,
        classification: str,
        topics: tuple[str, ...],
        entities: tuple[str, ...],
        fields: tuple[str, ...],
        calculation_limited: bool,
        request_level: str,
        contract: dict,
    ) -> str:
        lines = [
            f"نسخه نمایه دانش: {self.version}",
            f"طبقه‌بندی پوشش: {classification}",
            f"سطح درخواست: {request_level}",
            f"موضوع‌های شناسایی‌شده: {', '.join(topics) if topics else 'هیچ‌کدام'}",
            f"موجودیت‌های صریح: {', '.join(entities) if entities else 'هیچ‌کدام'}",
            f"ویژگی‌های درخواستی: {', '.join(fields) if fields else 'هیچ‌کدام'}",
            f"قرارداد پاسخ: {contract.get('instruction', 'فقط به درخواست فعلی پاسخ دهید.')}",
        ]
        if calculation_limited:
            lines.append(f"سیاست محاسبه: {self.data['calculation_policy']}")
        return "\n".join(lines)

    def direct_response(self, decision: ScopeDecision) -> str | None:
        if decision.request_level == "unsupported":
            return self.outside_world_response
        if decision.request_level == "broad_clarification":
            return str(self.data["request_planner"]["broad_clarification_response"])
        return None

    def project_evidence(self, results: list, decision: ScopeDecision) -> str:
        """Expose only evidence appropriate for the chosen request level.

        Nuanced modes retain normal retrieved prose. Only category listings and
        accommodation calculations receive a narrower, deterministic view.
        """
        if decision.request_level == "category_overview":
            for topic_id in decision.topic_ids:
                overview = self._category_overviews.get(topic_id)
                if not overview:
                    continue
                rows = [str(overview.get("intro", ""))]
                for item in overview.get("items", []):
                    label = str(item["name"])
                    identifying = str(item.get("identifying_property", "")).strip()
                    rows.append(f"- {label}: {identifying}" if identifying else f"- {label}")
                return "\n".join(row for row in rows if row)

        filtered = list(results)
        if (
            decision.request_level == "calculation_limited"
            and "accommodation" in decision.topic_ids
        ):
            # Seasonal tourism indices do not establish a percentage change for
            # each lodging price. Do not expose them to lodging calculations.
            filtered = [item for item in filtered if item.topic != "travel_cost"]
        return "\n\n".join(
            f"--- بخش {item.chunk_id} ---\n{item.text}" for item in filtered
        )

    def answer_passes_contract(self, answer: str, decision: ScopeDecision) -> bool:
        if decision.request_level == "category_overview":
            normalized = normalize_persian(answer)
            forbidden = self._normalized_values(
                self.data.get("request_planner", {}).get(
                    "category_overview_forbidden_details", []
                )
            )
            numeric_detail = bool(re.search(r"[۰-۹0-9]", answer))
            return not numeric_detail and not any(term in normalized for term in forbidden)
        if decision.request_level != "calculation_limited":
            return True
        normalized = normalize_persian(answer)
        arithmetic = re.search(r"[۰-۹0-9][^\n]{0,30}[×*÷=][^\n]{0,30}[۰-۹0-9]", answer)
        derived_total = any(
            term in normalized
            for term in ("جمع کل", "هزینه نهایی", "خواهد بود", "میشود", "می شود")
        )
        return not (arithmetic or derived_total)

    def contract_fallback(self, decision: ScopeDecision) -> str:
        if decision.request_level == "category_overview":
            projected = self.project_evidence([], decision)
            if projected:
                return projected
        if decision.request_level == "calculation_limited":
            return str(self.data["request_planner"]["calculation_fallback_response"])
        return self.not_documented_response

    def closed_world_context(self, query_with_context: str) -> str:
        normalized = normalize_persian(query_with_context)
        group = self.data.get("closed_world", {}).get("accommodation_services", {})
        entities = group.get("entities", {})
        accommodation_terms = ("اقامت", "هتل", "مهمان خانه", "خانه مسافر", "کلبه", "اردوگاه")
        mentioned = [name for name in entities if normalize_persian(name) in normalized]
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

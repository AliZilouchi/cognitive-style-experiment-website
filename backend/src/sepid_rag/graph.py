"""Minimal retrieve-then-answer LangGraph workflow."""

from __future__ import annotations

import json
import re
from typing import TypedDict

from .normalization import normalize_persian
from .prompts import (
    EVIDENCE_JUDGE_PROMPT,
    QUERY_RESOLVER_PROMPT,
    SYSTEM_PROMPT,
    VERIFIER_PROMPT,
    format_context,
)
from .task_contexts import classify_task_relevance, format_task_context, task_reminder
from .knowledge_scope import KnowledgeScope, ScopeDecision


class RagState(TypedDict, total=False):
    query: str
    task_id: str
    history: list[dict[str, str]]
    retrieval_query: str
    retrieved: list
    answer: str
    draft_answer: str
    clarification: str
    verification_status: str
    knowledge_classification: str
    knowledge_guidance: str
    closed_world_context: str
    task_relevance: str
    task_reminder: str
    request_level: str
    response_contract: str
    request_decision: ScopeDecision
    direct_answer: str
    projected_context: str
    retrieval_queries: list[str]
    social_answer: str
    raw_retrieved: list
    evidence_judge_status: str
    evidence_coverage: str
    query_resolver_status: str
    referenced_topics: list[str]


_FOLLOW_UP_MARKERS = {
    "آن",
    "اون",
    "این",
    "اینها",
    "آنها",
    "بقیه",
    "همه",
    "همان",
    "همین",
    "نسبت",
    "کدامشان",
    "همانها",
    "این موارد",
    "موارد بالا",
    "حالا",
}

_ATTACHED_REFERENCE = re.compile(
    r"(?:مرتب|مقایسه|توضیح|بررسی|قیمت|هزینه|ویژگی|امکانات|مجوز|قانون|جواب|پاسخ)(?:‌?شان|ش)(?:\s|$|[؟?!،,.])"
)
_COLLECTIVE_REFERENCE = re.compile(
    r"(?<!\w)(?:این موارد|موارد بالا|همانها|همان ها|همه اینها|همه آنها)(?!\w)"
)


def has_reference_marker(normalized: str) -> bool:
    return any(
        re.search(rf"(?<!\w){re.escape(marker)}(?!\w)", normalized)
        for marker in _FOLLOW_UP_MARKERS
    ) or bool(_ATTACHED_REFERENCE.search(normalized))


def recent_user_queries_for_collective_reference(
    query: str,
    history: list[dict[str, str]],
) -> list[str]:
    """Reuse prior user questions as retrieval queries for collective follow-ups."""
    if not _COLLECTIVE_REFERENCE.search(normalize_persian(query)):
        return []
    queries = []
    for item in history:
        if item.get("role") != "user":
            continue
        content = item.get("content", "").strip()
        if content and social_response(content) is None:
            queries.append(content)
    return queries[-5:]

_INCOMPLETE_ENDINGS = {
    "از",
    "با",
    "برای",
    "به",
    "درباره",
    "مثل",
    "مانند",
    "که",
    "یا",
    "و",
}

_SOCIAL_RESPONSES = {
    "سلام": "سلام! در خدمتم.",
    "درود": "درود! در خدمتم.",
    "ممنون": "خواهش می‌کنم.",
    "مرسی": "خواهش می‌کنم.",
    "متشکرم": "خواهش می‌کنم.",
    "سپاس": "خواهش می‌کنم.",
    "خداحافظ": "خداحافظ، موفق باشید.",
}


def social_response(query: str) -> str | None:
    """Handle tiny social turns without pretending the corpus lacks an answer."""
    normalized = normalize_persian(query).strip(" ؟?!،,.;:")
    return _SOCIAL_RESPONSES.get(normalized)


def build_retrieval_queries(query: str, resolved_query: str) -> list[str]:
    """Split only explicit multi-part messages; do not over-segment normal prose."""
    parts = [
        part.strip(" \n\t-–—؟?")
        for part in re.split(r"[؟?]+|\n+", normalize_persian(query))
        if part.strip(" \n\t-–—؟?")
    ]
    if len(parts) <= 1:
        return [resolved_query]
    return parts[:4]


def clarification_for_incomplete_query(query: str) -> str | None:
    """Catch plainly unfinished messages before they become false no-result answers."""

    normalized = normalize_persian(query).strip(" ؟?!،,.;:")
    if not normalized:
        return "لطفاً پرسش خود را کمی کامل‌تر بنویسید."
    tokens = normalized.split()
    if tokens and tokens[-1] in _INCOMPLETE_ENDINGS:
        return "منظورتان را کمی کامل‌تر می‌کنید؟"
    return None


def retrieval_scope_for_task(task_id: str) -> str | None:
    """Every participant-facing context searches the same frozen corpus."""
    return None


def build_retrieval_query(
    query: str,
    history: list[dict[str, str]],
    known_entities: set[str],
) -> str:
    """Resolve short/referential follow-ups without rewriting clear questions."""

    normalized = normalize_persian(query)
    has_marker = has_reference_marker(normalized)
    has_named_entity = any(
        normalize_persian(entity) in normalized for entity in known_entities
    )
    if not history or not has_marker or has_named_entity:
        return query

    recent = [
        item.get("content", "").strip()
        for item in history[-6:]
        if item.get("role") in {"user", "assistant"} and item.get("content", "").strip()
    ][-3:]
    if not recent:
        return query
    return "\n".join(["زمینه گفت‌وگوی اخیر:", *recent, "پرسش فعلی:", query])


def needs_history_resolution(
    query: str,
    history: list[dict[str, str]],
    known_entities: set[str] | None = None,
) -> bool:
    """Use the resolver only when the current turn actually depends on history."""
    if not history:
        return False
    normalized = normalize_persian(query)
    has_named_entity = any(
        normalize_persian(entity) in normalized for entity in (known_entities or set())
    )
    if has_named_entity:
        return False
    return has_reference_marker(normalized)


def clean_model_content(content: object) -> str:
    """Remove provider reasoning wrappers without exposing hidden reasoning."""

    cleaned = str(content).strip()
    if "<think>" in cleaned:
        if "</think>" not in cleaned:
            raise RuntimeError("Model reasoning leaked and the final answer was truncated")
        cleaned = cleaned.rsplit("</think>", maxsplit=1)[-1].strip()
    return cleaned


def extract_verified_answer(content: object) -> str | None:
    """Parse the verifier envelope; malformed audits never replace a valid draft."""

    cleaned = clean_model_content(content)
    start = "<verified_answer>"
    end = "</verified_answer>"
    if start not in cleaned or end not in cleaned:
        return None
    answer = cleaned.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0].strip()
    return answer or None


def extract_evidence_decision(content: object) -> dict | None:
    """Parse and minimally validate the post-retrieval judge envelope."""
    cleaned = clean_model_content(content)
    start = "<evidence_decision>"
    end = "</evidence_decision>"
    if start not in cleaned or end not in cleaned:
        return None
    payload = cleaned.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0].strip()
    try:
        result = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(result, dict):
        return None
    if result.get("classification") not in {"supported", "unsupported"}:
        return None
    if not isinstance(result.get("selected_chunk_ids", []), list):
        return None
    coverage_items = result.get("coverage_items")
    if not isinstance(coverage_items, list) or not coverage_items:
        return None
    for item in coverage_items:
        if (
            not isinstance(item, dict)
            or item.get("status") not in {"direct", "partial", "missing"}
            or not isinstance(item.get("selected_chunk_ids", []), list)
        ):
            return None
    return result


def extract_query_resolution(content: object) -> dict | None:
    """Parse a history-aware retrieval plan without accepting model prose."""
    cleaned = clean_model_content(content)
    start = "<query_resolution>"
    end = "</query_resolution>"
    if start not in cleaned or end not in cleaned:
        return None
    payload = cleaned.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0].strip()
    try:
        result = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(result, dict) or result.get("status") not in {
        "independent",
        "resolved",
        "unresolved",
    }:
        return None
    if not isinstance(result.get("standalone_query"), str):
        return None
    queries = result.get("retrieval_queries")
    if not isinstance(queries, list) or not all(isinstance(item, str) for item in queries):
        return None
    return result


def build_graph(retriever, settings, knowledge_scope: KnowledgeScope):
    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("Install project dependencies to use the LangGraph workflow") from exc

    llm = None
    resolver_llm = None
    resolver_model = getattr(settings, "resolver_model", "") or settings.llm_model
    resolver_max_tokens = getattr(settings, "resolver_max_tokens", 250)
    resolver_timeout = getattr(settings, "resolver_timeout_seconds", 8)
    if settings.llm_provider == "together":
        try:
            from langchain_together import ChatTogether
        except ImportError as exc:
            raise RuntimeError("langchain-together is not installed") from exc
        llm = ChatTogether(
            model=settings.llm_model,
            temperature=0,
            max_tokens=settings.llm_max_tokens,
            max_retries=0,
            timeout=60,
        )
        resolver_llm = ChatTogether(
            model=resolver_model,
            temperature=0,
            max_tokens=resolver_max_tokens,
            max_retries=0,
            timeout=resolver_timeout,
        )
    elif settings.llm_provider == "groq":
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise RuntimeError("langchain-groq is not installed") from exc
        llm = ChatGroq(
            model=settings.llm_model,
            temperature=0,
            max_tokens=settings.llm_max_tokens,
            max_retries=0,
            timeout=60,
            reasoning_format="hidden",
            reasoning_effort="none",
        )
        resolver_llm = ChatGroq(
            model=resolver_model,
            temperature=0,
            max_tokens=resolver_max_tokens,
            max_retries=0,
            timeout=resolver_timeout,
            reasoning_format="hidden",
            reasoning_effort="none",
        )
    elif settings.llm_provider == "openrouter":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("langchain-openai is not installed") from exc
        headers = {}
        if settings.openrouter_http_referer:
            headers["HTTP-Referer"] = settings.openrouter_http_referer
        if settings.openrouter_app_title:
            headers["X-Title"] = settings.openrouter_app_title
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers=headers or None,
            temperature=0,
            max_tokens=settings.llm_max_tokens,
            max_retries=0,
            timeout=60,
        )
        resolver_llm = ChatOpenAI(
            model=resolver_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers=headers or None,
            temperature=0,
            max_tokens=resolver_max_tokens,
            max_retries=0,
            timeout=resolver_timeout,
        )
    elif settings.llm_provider == "avalai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("langchain-openai is not installed") from exc
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.avalai_api_key,
            base_url=settings.avalai_base_url,
            temperature=0,
            max_tokens=settings.llm_max_tokens,
            max_retries=0,
            timeout=60,
        )
        resolver_llm = ChatOpenAI(
            model=resolver_model,
            api_key=settings.avalai_api_key,
            base_url=settings.avalai_base_url,
            temperature=0,
            max_tokens=resolver_max_tokens,
            max_retries=0,
            timeout=resolver_timeout,
        )

    def resolve_query(state: RagState) -> dict:
        social = social_response(state["query"])
        if social:
            return {
                "retrieval_query": state["query"],
                "retrieval_queries": [],
                "retrieved": [],
                "social_answer": social,
                "query_resolver_status": "not_needed",
            }
        clarification = clarification_for_incomplete_query(state["query"])
        if clarification:
            return {
                "retrieval_query": state["query"],
                "retrieval_queries": [],
                "retrieved": [],
                "clarification": clarification,
                "query_resolver_status": "not_needed",
            }
        recent_history = [
            item for item in state.get("history", [])[-12:]
            if item.get("role") == "user"
        ][-6:]
        history_text = "\n".join(
            f"user: {item.get('content', '').strip()}"
            for item in recent_history
            if item.get("content", "").strip()
        )
        resolution = None
        if resolver_llm is not None:
            try:
                resolution = extract_query_resolution(resolver_llm.invoke([
                    SystemMessage(content=QUERY_RESOLVER_PROMPT),
                    HumanMessage(content=(
                        f"تاریخچه اخیر:\n{history_text}\n\n"
                        f"پرسش فعلی:\n{state['query']}"
                    )),
                ]).content)
            except Exception:
                resolution = None

        if resolution is not None and resolution["status"] == "independent":
            return {
                "retrieval_query": state["query"],
                "retrieval_queries": [state["query"]],
                "query_resolver_status": "independent",
                "referenced_topics": [],
            }

        history_queries = recent_user_queries_for_collective_reference(
            state["query"], recent_history
        )
        if resolution is None or resolution["status"] != "resolved":
            fallback_query = state["query"]
            fallback_queries = build_retrieval_queries(state["query"], fallback_query)
            fallback_queries = list(dict.fromkeys([*fallback_queries, *history_queries]))[:6]
            return {
                "retrieval_query": fallback_query,
                "retrieval_queries": fallback_queries,
                "query_resolver_status": "fallback",
                "referenced_topics": [],
            }

        standalone = resolution["standalone_query"].strip() or state["query"]
        queries = [
            item.strip() for item in resolution["retrieval_queries"]
            if item.strip()
        ][:6]
        if not queries:
            queries = [standalone]
        queries = list(dict.fromkeys([*queries, *history_queries]))[:6]
        topics = [
            str(item).strip() for item in resolution.get("referenced_topics", [])
            if str(item).strip()
        ][:8]
        return {
            "retrieval_query": standalone,
            "retrieval_queries": queries,
            "query_resolver_status": "resolved",
            "referenced_topics": topics,
        }

    def retrieve(state: RagState) -> dict:
        if state.get("social_answer") or state.get("clarification"):
            return {"retrieved": [], "raw_retrieved": []}
        retrieval_scope = retrieval_scope_for_task(state["task_id"])
        retrieval_query = state.get("retrieval_query", state["query"])
        retrieval_queries = state.get("retrieval_queries") or [retrieval_query]
        # Retrieval deliberately happens before Knowledge Index classification.
        # A missing alias must never suppress valid evidence (for example events).
        if hasattr(retriever, "search_many"):
            results = retriever.search_many(
                retrieval_queries,
                retrieval_scope,
                preferred_node_types=(),
                limit=settings.top_k,
            )
        else:
            results = retriever.search(
                retrieval_query,
                retrieval_scope,
                preferred_node_types=(),
                limit=settings.top_k,
            )
        return {
            "retrieval_query": retrieval_query,
            "retrieval_queries": retrieval_queries,
            "retrieved": results,
            "raw_retrieved": results,
        }

    def judge_evidence(state: RagState) -> dict:
        if state.get("social_answer") or state.get("clarification"):
            return {"evidence_judge_status": "not_needed"}

        results = state.get("raw_retrieved", state.get("retrieved", []))
        entities = {
            entity for document in retriever.documents for entity in document.entities
        }
        baseline = knowledge_scope.classify(
            state["query"], entities, contextual_query=state.get("retrieval_query")
        )
        judge_result = None
        if settings.llm_provider != "echo" and results:
            candidate_context = "\n\n".join(
                f"chunk_id={item.chunk_id}\nnode_type={item.node_type}\n"
                f"topic={item.topic}\ntext={item.text}"
                for item in results
            )
            messages = [
                SystemMessage(content=EVIDENCE_JUDGE_PROMPT),
                HumanMessage(content=(
                    f"زمینه فعالیت:\n{format_task_context(state['task_id'])}\n\n"
                    f"پرسش فعلی:\n{state['query']}\n\n"
                    f"صورت حل‌شده برای ارجاع مکالمه‌ای:\n"
                    f"{state.get('retrieval_query', state['query'])}\n\n"
                    f"نامزدهای بازیابی‌شده:\n{candidate_context}"
                )),
            ]
            try:
                judge_result = extract_evidence_decision(llm.invoke(messages).content)
            except Exception:
                judge_result = None

        valid_ids = {item.chunk_id for item in results}
        if judge_result is not None:
            selected_ids = [
                str(item) for item in judge_result.get("selected_chunk_ids", [])
                if str(item) in valid_ids
            ][:6]
            classification = str(judge_result["classification"])
            # A supported judgment without any valid evidence is malformed.
            if classification == "supported" and not selected_ids:
                judge_result = None

        if judge_result is None:
            # Safe fallback: retrieval evidence remains available and an unknown
            # alias cannot close the corpus. The answer verifier still guards it.
            selected = list(results[: min(6, len(results))])
            classification = "supported" if selected else "unsupported"
            request_level = (
                baseline.request_level
                if baseline.request_level not in {"unsupported", "broad_clarification"}
                else "single_fact"
            )
            coverage = "داور شواهد در دسترس نبود؛ نتایج برتر بازیابی حفظ شدند."
            answer_instruction = "فقط با شواهد منتخب به پرسش فعلی پاسخ دهید."
            judge_status = "fallback"
        else:
            selected = [item for item in results if item.chunk_id in selected_ids]
            selected.sort(key=lambda item: selected_ids.index(item.chunk_id))
            classification = str(judge_result["classification"])
            request_level = baseline.request_level
            if request_level in {"unsupported", "broad_clarification"}:
                request_level = str(judge_result.get("request_level", "single_fact"))
            coverage = str(judge_result.get("coverage", ""))
            coverage_items = judge_result.get("coverage_items", [])
            coverage_detail = "\n".join(
                f"- {item.get('question_part', 'بخش پرسش')}: {item.get('status')}"
                for item in coverage_items
            )
            if coverage_detail:
                coverage = "\n".join(item for item in (coverage, coverage_detail) if item)
            answer_instruction = str(judge_result.get("answer_instruction", ""))
            judge_status = "judged"

        decision = knowledge_scope.apply_evidence_judgment(
            baseline,
            classification,
            request_level,
            "\n".join(item for item in (coverage, answer_instruction) if item),
        )
        relevance = classify_task_relevance(state["task_id"], decision.topic_ids)
        recent_user_turns = [
            item.get("content", "")
            for item in state.get("history", [])[-6:]
            if item.get("role") == "user"
        ]
        prior_outside = sum(
            1
            for item in recent_user_turns[-2:]
            if classify_task_relevance(
                state["task_id"], knowledge_scope.classify(item, entities).topic_ids
            ) == "outside_task"
        )
        reminder = (
            task_reminder(state["task_id"])
            if relevance == "outside_task" and prior_outside >= 2
            else ""
        )
        direct_answer = knowledge_scope.direct_response(decision)
        if not direct_answer and decision.request_level == "category_overview":
            direct_answer = knowledge_scope.category_overview_response(decision)
        projected = knowledge_scope.project_evidence(selected, decision)
        closed_world = knowledge_scope.closed_world_context(
            state.get("retrieval_query", state["query"]), decision
        )
        knowledge_constraints = knowledge_scope.knowledge_constraints(
            state.get("retrieval_query", state["query"])
        )
        authorized_evidence = "\n\n".join(
            item for item in (knowledge_constraints, closed_world, projected) if item
        )
        return {
            "retrieved": selected,
            "knowledge_classification": decision.classification,
            "knowledge_guidance": decision.guidance,
            "closed_world_context": closed_world,
            "task_relevance": relevance,
            "task_reminder": reminder,
            "request_level": decision.request_level,
            "response_contract": decision.response_contract,
            "request_decision": decision,
            "direct_answer": direct_answer or "",
            "projected_context": authorized_evidence,
            "evidence_judge_status": judge_status,
            "evidence_coverage": coverage,
        }

    def draft_answer(state: RagState) -> dict:
        if state.get("social_answer"):
            return {
                "draft_answer": state["social_answer"],
                "answer": state["social_answer"],
                "verification_status": "not_needed",
            }
        if state.get("clarification"):
            return {
                "draft_answer": state["clarification"],
                "answer": state["clarification"],
                "verification_status": "not_needed",
            }
        if state.get("direct_answer"):
            return {
                "draft_answer": state["direct_answer"],
                "answer": state["direct_answer"],
                "verification_status": "not_needed",
            }
        results = state["retrieved"]
        if settings.llm_provider == "echo":
            ids = "، ".join(item.source_id for item in results)
            answer = (
                    "حالت آزمایشی بدون مدل زبانی فعال است. "
                    f"منابع بازیابی‌شده: {ids}"
                )
            return {
                "draft_answer": answer,
                "answer": answer,
                "verification_status": "not_available",
            }

        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for item in state.get("history", [])[-8:]:
            role = item.get("role")
            content = item.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        messages.append(
            HumanMessage(
                content=(
                    f"شناسهٔ فعالیت فعلی: {state['task_id']}\n"
                    f"زمینه و مرز فعالیت:\n{format_task_context(state['task_id'])}\n\n"
                    f"تصمیم نمایه دانش:\n{state.get('knowledge_guidance', '')}\n\n"
                    f"قرارداد الزام‌آور پاسخ:\n{state.get('response_contract', '')}\n\n"
                    f"ارتباط با فعالیت فعلی: {state.get('task_relevance', 'unknown')}\n"
                    f"تنها شواهد مجاز برای پاسخ:\n{state.get('projected_context', format_context(results)) or 'داده پایه مرتبطی بازیابی نشد.'}\n\n"
                    f"صورت مستقل و حل‌شدهٔ پرسش برای فهم ارجاع‌ها:\n{state.get('retrieval_query', state['query'])}\n\n"
                    f"پرسش فعلی کاربر:\n{state['query']}"
                )
            )
        )
        response = llm.invoke(messages)
        content = clean_model_content(response.content)
        return {"draft_answer": content, "answer": content}

    def verify_answer(state: RagState) -> dict:
        if (
            state.get("clarification")
            or state.get("social_answer")
            or settings.llm_provider == "echo"
            or not settings.enable_response_verifier
            or state.get("direct_answer")
        ):
            final_answer = state["draft_answer"]
            decision = state.get("request_decision")
            if decision and not knowledge_scope.answer_passes_contract(final_answer, decision):
                final_answer = knowledge_scope.contract_fallback(decision)
            if state.get("task_reminder") and state["task_reminder"] not in final_answer:
                final_answer = f"{final_answer}\n\n{state['task_reminder']}"
            return {
                "answer": final_answer,
                "verification_status": state.get("verification_status", "disabled"),
            }

        evidence = state.get("projected_context", format_context(state["retrieved"]))
        audit_messages = [
            SystemMessage(content=VERIFIER_PROMPT),
            HumanMessage(
                content=(
                    f"زمینه و مرز فعالیت:\n{format_task_context(state['task_id'])}\n\n"
                    f"تصمیم نمایه دانش:\n{state.get('knowledge_guidance', '')}\n\n"
                    f"قرارداد الزام‌آور پاسخ:\n{state.get('response_contract', '')}\n\n"
                    f"پرسش فعلی:\n{state['query']}\n\n"
                    f"منابع مجاز:\n{evidence}\n\n"
                    f"پیش‌نویس برای ممیزی:\n{state['draft_answer']}"
                )
            ),
        ]
        try:
            response = llm.invoke(audit_messages)
            verified = extract_verified_answer(response.content)
        except Exception:
            # A verifier outage must not turn an otherwise valid participant turn
            # into an endless loading/error loop. The unverified status is exposed
            # to the API for monitoring.
            verified = None
        if verified is None:
            final_answer = state["draft_answer"]
            decision = state.get("request_decision")
            if decision and not knowledge_scope.answer_passes_contract(final_answer, decision):
                final_answer = knowledge_scope.contract_fallback(decision)
            if state.get("task_reminder") and state["task_reminder"] not in final_answer:
                final_answer = f"{final_answer}\n\n{state['task_reminder']}"
            return {
                "answer": final_answer,
                "verification_status": "fallback_to_draft",
            }
        decision = state.get("request_decision")
        if decision and not knowledge_scope.answer_passes_contract(verified, decision):
            verified = knowledge_scope.contract_fallback(decision)
        if state.get("task_reminder") and state["task_reminder"] not in verified:
            verified = f"{verified}\n\n{state['task_reminder']}"
        return {
            "answer": verified,
            "verification_status": (
                "verified_unchanged"
                if verified == state["draft_answer"]
                else "verified_revised"
            ),
        }

    graph = StateGraph(RagState)
    graph.add_node("resolve_query", resolve_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("judge_evidence", judge_evidence)
    graph.add_node("draft_answer", draft_answer)
    graph.add_node("verify_answer", verify_answer)
    graph.add_edge(START, "resolve_query")
    graph.add_edge("resolve_query", "retrieve")
    graph.add_edge("retrieve", "judge_evidence")
    graph.add_edge("judge_evidence", "draft_answer")
    graph.add_edge("draft_answer", "verify_answer")
    graph.add_edge("verify_answer", END)
    return graph.compile()

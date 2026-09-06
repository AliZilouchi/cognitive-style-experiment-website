"""Minimal retrieve-then-answer LangGraph workflow."""

from __future__ import annotations

from typing import TypedDict

from .normalization import normalize_persian
from .prompts import SYSTEM_PROMPT, VERIFIER_PROMPT, format_context
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
    "دقیقاً",
    "دقیقا",
    "کدامشان",
    "چطور",
    "چگونه",
    "چرا",
}

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
    tokens = set(normalized.split())
    has_marker = bool(tokens & _FOLLOW_UP_MARKERS)
    has_named_entity = any(
        normalize_persian(entity) in normalized for entity in known_entities
    )
    is_short_subjectless = len(tokens) <= 6 and not has_named_entity
    if not history or not (has_marker or is_short_subjectless):
        return query

    recent = [
        item.get("content", "").strip()
        for item in history[-6:]
        if item.get("role") in {"user", "assistant"} and item.get("content", "").strip()
    ][-3:]
    if not recent:
        return query
    return "\n".join(["زمینه گفت‌وگوی اخیر:", *recent, "پرسش فعلی:", query])


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


def build_graph(retriever, settings, knowledge_scope: KnowledgeScope):
    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("Install project dependencies to use the LangGraph workflow") from exc

    llm = None
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

    def retrieve(state: RagState) -> dict:
        clarification = clarification_for_incomplete_query(state["query"])
        if clarification:
            return {
                "retrieval_query": state["query"],
                "retrieved": [],
                "clarification": clarification,
            }
        retrieval_scope = retrieval_scope_for_task(state["task_id"])
        entities = {
            entity
            for document in retriever.documents
            if retrieval_scope is None or retrieval_scope in document.task_ids
            for entity in document.entities
        }
        retrieval_query = build_retrieval_query(
            state["query"], state.get("history", []), entities
        )
        decision = knowledge_scope.classify(
            state["query"], entities, contextual_query=retrieval_query
        )
        closed_world = knowledge_scope.closed_world_context(retrieval_query)
        relevance = classify_task_relevance(state["task_id"], decision.topic_ids)
        reminder = task_reminder(state["task_id"]) if relevance == "outside_task" else ""
        direct_answer = knowledge_scope.direct_response(decision)
        if direct_answer is not None:
            return {
                "retrieval_query": retrieval_query,
                "retrieved": [],
                "knowledge_classification": decision.classification,
                "knowledge_guidance": decision.guidance,
                "closed_world_context": closed_world,
                "task_relevance": relevance,
                "task_reminder": reminder,
                "request_level": decision.request_level,
                "response_contract": decision.response_contract,
                "request_decision": decision,
                "direct_answer": direct_answer,
            }
        return {
            "retrieval_query": retrieval_query,
            "retrieved": retriever.search(
                retrieval_query,
                retrieval_scope,
                preferred_node_types=decision.preferred_node_types,
                limit=decision.retrieval_limit,
            ),
            "knowledge_classification": decision.classification,
            "knowledge_guidance": decision.guidance,
            "closed_world_context": closed_world,
            "task_relevance": relevance,
            "task_reminder": reminder,
            "request_level": decision.request_level,
            "response_contract": decision.response_contract,
            "request_decision": decision,
        }

    def draft_answer(state: RagState) -> dict:
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
                    f"اطلاعات صریحِ دامنه بسته:\n{state.get('closed_world_context') or 'موردی فعال نیست.'}\n\n"
                    f"منابع بازیابی‌شده:\n{format_context(results)}\n\n"
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

        evidence = format_context(state["retrieved"])
        audit_messages = [
            SystemMessage(content=VERIFIER_PROMPT),
            HumanMessage(
                content=(
                    f"زمینه و مرز فعالیت:\n{format_task_context(state['task_id'])}\n\n"
                    f"تصمیم نمایه دانش:\n{state.get('knowledge_guidance', '')}\n\n"
                    f"قرارداد الزام‌آور پاسخ:\n{state.get('response_contract', '')}\n\n"
                    f"اطلاعات صریحِ دامنه بسته:\n{state.get('closed_world_context') or 'موردی فعال نیست.'}\n\n"
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
    graph.add_node("retrieve", retrieve)
    graph.add_node("draft_answer", draft_answer)
    graph.add_node("verify_answer", verify_answer)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "draft_answer")
    graph.add_edge("draft_answer", "verify_answer")
    graph.add_edge("verify_answer", END)
    return graph.compile()

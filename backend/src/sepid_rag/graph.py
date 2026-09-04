"""Minimal retrieve-then-answer LangGraph workflow."""

from __future__ import annotations

from typing import TypedDict

from .normalization import normalize_persian
from .prompts import SYSTEM_PROMPT, format_context


class RagState(TypedDict, total=False):
    query: str
    task_id: str
    history: list[dict[str, str]]
    retrieval_query: str
    retrieved: list
    answer: str


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


def build_graph(retriever, settings):
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
        entities = {
            entity
            for document in retriever.documents
            if state["task_id"] in document.task_ids
            for entity in document.entities
        }
        retrieval_query = build_retrieval_query(
            state["query"], state.get("history", []), entities
        )
        return {
            "retrieval_query": retrieval_query,
            "retrieved": retriever.search(retrieval_query, state["task_id"]),
        }

    def answer(state: RagState) -> dict:
        results = state["retrieved"]
        if settings.llm_provider == "echo":
            ids = "، ".join(item.source_id for item in results)
            return {
                "answer": (
                    "حالت آزمایشی بدون مدل زبانی فعال است. "
                    f"منابع بازیابی‌شده: {ids}"
                )
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
                    f"منابع بازیابی‌شده:\n{format_context(results)}\n\n"
                    f"پرسش فعلی کاربر:\n{state['query']}"
                )
            )
        )
        response = llm.invoke(messages)
        content = str(response.content)
        if "<think>" in content:
            if "</think>" not in content:
                raise RuntimeError("Model reasoning leaked and the final answer was truncated")
            content = content.rsplit("</think>", maxsplit=1)[-1].strip()
        return {"answer": content}

    graph = StateGraph(RagState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("answer", answer)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    return graph.compile()

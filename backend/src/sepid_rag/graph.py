"""Minimal retrieve-then-answer LangGraph workflow."""

from __future__ import annotations

from typing import TypedDict

from .prompts import SYSTEM_PROMPT, format_context


class RagState(TypedDict, total=False):
    query: str
    history: list[dict[str, str]]
    retrieval_query: str
    retrieved: list
    answer: str


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

    def retrieve(state: RagState) -> dict:
        recent_user_turns = [
            item.get("content", "")
            for item in state.get("history", [])
            if item.get("role") == "user"
        ][-2:]
        retrieval_query = "\n".join([*recent_user_turns, state["query"]])
        return {
            "retrieval_query": retrieval_query,
            "retrieved": retriever.search(retrieval_query),
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

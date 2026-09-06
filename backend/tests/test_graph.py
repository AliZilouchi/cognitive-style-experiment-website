import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from sepid_rag.graph import (
    build_graph,
    build_retrieval_queries,
    build_retrieval_query,
    retrieval_scope_for_task,
    social_response,
)
from sepid_rag.knowledge_scope import KnowledgeScope


class _Message:
    def __init__(self, content):
        self.content = content


class _CompiledGraph:
    def __init__(self, nodes):
        self.nodes = nodes

    def invoke(self, state):
        result = dict(state)
        for name in ("retrieve", "judge_evidence", "draft_answer", "verify_answer"):
            result.update(self.nodes[name](result))
        return result


class _StateGraph:
    def __init__(self, state_type):
        self.nodes = {}

    def add_node(self, name, function):
        self.nodes[name] = function

    def add_edge(self, start, end):
        pass

    def compile(self):
        return _CompiledGraph(self.nodes)


class _FakeChat:
    calls = []

    def __init__(self, **kwargs):
        pass

    def invoke(self, messages):
        self.calls.append(messages)
        if len(self.calls) == 1:
            return SimpleNamespace(content=(
                '<evidence_decision>{"classification":"supported",'
                '"request_level":"single_fact",'
                '"selected_chunk_ids":["SHARED-FACT-ISLAND-ACCESS"],'
                '"coverage":"پوشش مستقیم",'
                '"answer_instruction":"فقط مسیر ورود را بگو"}</evidence_decision>'
            ))
        if len(self.calls) == 2:
            return SimpleNamespace(content="جزیره فرودگاه مسافری دارد.")
        return SimpleNamespace(
            content=(
                "<verified_answer>جزیره فرودگاه مسافری ندارد و راه معمول ورود، "
                "شناور مسافری از بندر آفتاب است.</verified_answer>"
            )
        )


class _Retrieved:
    source_id = "E12"
    source_ids = ("E12",)
    chunk_id = "SHARED-FACT-ISLAND-ACCESS"
    node_type = "fact"
    topic = "transport_access"
    text = "جزیره فرودگاه مسافری ندارد و راه معمول ورود، شناور مسافری از بندر آفتاب است."


class _Retriever:
    documents = []

    def search(self, query, task_id, preferred_node_types=(), limit=None):
        return [_Retrieved()]


class RetrievalQueryTests(unittest.TestCase):
    def test_social_turns_bypass_retrieval(self):
        self.assertEqual(social_response("سلام"), "سلام! در خدمتم.")
        self.assertIsNone(social_response("آب و هوای جزیره چگونه است؟"))

    def test_explicit_multi_part_query_is_split(self):
        parts = build_retrieval_queries(
            "کدام اقامتگاه نزدیک بازار است؟ کدام‌یک صبحانه دارد؟",
            "unused",
        )
        self.assertEqual(len(parts), 2)

    def test_every_participant_context_searches_the_complete_corpus(self):
        self.assertIsNone(retrieval_scope_for_task("free_chat"))
        self.assertIsNone(retrieval_scope_for_task("task_1"))
        self.assertIsNone(retrieval_scope_for_task("task_2"))
        self.assertIsNone(retrieval_scope_for_task("task_3"))

    def test_clear_standalone_query_is_not_broadened(self):
        query = "قیمت هتل صدف چقدر است؟"
        self.assertEqual(
            build_retrieval_query(
                query,
                [{"role": "user", "content": "آبخوری کجاست؟"}],
                {"هتل صدف"},
            ),
            query,
        )

    def test_referential_follow_up_uses_recent_context(self):
        result = build_retrieval_query(
            "نسبت به بقیه چطور است؟",
            [
                {"role": "user", "content": "درباره اردوگاه چشمه بگو"},
                {"role": "assistant", "content": "هر محل چادر سه نفر ظرفیت دارد."},
            ],
            {"اردوگاه چشمه"},
        )
        self.assertIn("اردوگاه چشمه", result)
        self.assertIn("نسبت به بقیه چطور است؟", result)

    def test_incomplete_short_question_uses_context(self):
        result = build_retrieval_query(
            "و مجوزش؟",
            [{"role": "user", "content": "قیمت کلبه‌های نارون چقدر است؟"}],
            {"کلبه‌های نارون"},
        )
        self.assertIn("کلبه‌های نارون", result)

    def test_two_pass_pipeline_revises_an_unsupported_draft(self):
        langchain_messages = ModuleType("langchain_core.messages")
        langchain_messages.AIMessage = _Message
        langchain_messages.HumanMessage = _Message
        langchain_messages.SystemMessage = _Message
        langgraph_graph = ModuleType("langgraph.graph")
        langgraph_graph.END = "END"
        langgraph_graph.START = "START"
        langgraph_graph.StateGraph = _StateGraph
        langchain_openai = ModuleType("langchain_openai")
        langchain_openai.ChatOpenAI = _FakeChat
        modules = {
            "langchain_core": ModuleType("langchain_core"),
            "langchain_core.messages": langchain_messages,
            "langgraph": ModuleType("langgraph"),
            "langgraph.graph": langgraph_graph,
            "langchain_openai": langchain_openai,
        }
        settings = SimpleNamespace(
            llm_provider="avalai",
            llm_model="fake-model",
            llm_max_tokens=700,
            top_k=8,
            avalai_api_key="fake-key",
            avalai_base_url="https://example.invalid/v1",
            enable_response_verifier=True,
        )
        _FakeChat.calls = []
        with patch.dict(sys.modules, modules):
            knowledge_scope = KnowledgeScope(
                {
                    "version": "test-scope",
                    "outside_world_response": "در دسترس نیست.",
                    "not_documented_response": "مشخص نشده است.",
                    "topics": [{"id": "transport", "aliases": ["رسیدن", "جزیره"]}],
                    "outside_world_indicators": ["بورس"],
                    "calculation_indicators": ["حساب کن"],
                    "calculation_policy": "محاسبه نکن.",
                    "closed_world": {},
                }
            )
            graph = build_graph(_Retriever(), settings, knowledge_scope)
            result = graph.invoke(
                {"query": "چطور به جزیره برسیم؟", "task_id": "free_chat", "history": []}
            )
        self.assertEqual(len(_FakeChat.calls), 3)
        self.assertEqual(result["verification_status"], "verified_revised")
        self.assertIn("فرودگاه مسافری ندارد", result["answer"])


if __name__ == "__main__":
    unittest.main()

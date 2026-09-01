from pathlib import Path
import json

from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.fixture(autouse=True)
def disable_external_deepseek(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")


def test_assistant_returns_controlled_intents(tmp_path: Path) -> None:
    api = TestClient(create_app(tmp_path))
    product = api.post("/api/v1/assistant/chat", json={"text": "查牛奶", "user_id": "demo-elder"}).json()["data"]
    assert product["intent"] == "product_search"
    assert product["action"]["product_ids"] == ["milk-001"]
    assert product["needs_confirmation"] is False

    order = api.post("/api/v1/assistant/chat", json={"text": "查订单"}).json()["data"]
    assert order["intent"] == "order_list"
    assert order["action"]["type"] == "orders"

    payment = api.post("/api/v1/assistant/chat", json={"text": "让家人付款"}).json()["data"]
    assert payment["intent"] == "family_payment_entry"
    assert payment["needs_confirmation"] is True

    knowledge = api.post("/api/v1/assistant/chat", json={"text": "退货怎么申请"}).json()["data"]
    assert knowledge["intent"] == "knowledge_query"
    assert knowledge["action"]["type"] == "knowledge_search"
    assert knowledge["action"]["sources"][0]["source_id"] == "faq-after-sale"


def test_knowledge_search_returns_versioned_sources(tmp_path: Path) -> None:
    api = TestClient(create_app(tmp_path))
    response = api.get("/api/v1/knowledge/search", params={"q": "家人怎么代付"})
    assert response.status_code == 200
    source = response.json()["data"][0]
    assert source["source_id"] == "faq-family"
    assert source["version"] == "v1"


def test_assistant_does_not_execute_high_risk_actions(tmp_path: Path) -> None:
    api = TestClient(create_app(tmp_path))
    after_sale = api.post("/api/v1/assistant/chat", json={"text": "申请退货"}).json()["data"]
    assert after_sale["intent"] == "after_sale_entry"
    assert after_sale["action"] == {"type": "orders", "filter": "delivered"}
    records = json.loads((tmp_path / "after_sales.json").read_text(encoding="utf-8"))["items"]
    assert len(records) == 1

    invalid = api.post("/api/v1/assistant/chat", json={"text": ""})
    assert invalid.status_code == 422


def test_assistant_can_use_deepseek_adapter_without_exposing_key(tmp_path: Path, monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            content = json.dumps({"intent": "product_search", "reply": "找到了牛奶。", "action": {"type": "product_search", "query": "牛奶"}, "needs_confirmation": False, "suggestions": ["查订单"]}, ensure_ascii=False)
            return {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}}

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-returned")
    monkeypatch.setattr("app.assistant_service.httpx.AsyncClient", FakeClient)
    result = TestClient(create_app(tmp_path)).post("/api/v1/assistant/chat", json={"text": "帮我找牛奶"}).json()["data"]
    assert result["provider"] == "deepseek"
    assert result["model"] == "deepseek-v4-pro"
    assert result["action"]["product_ids"] == ["milk-001"]
    assert "test-key-not-returned" not in str(result)


def test_assistant_executes_only_approved_readonly_tools(tmp_path: Path, monkeypatch) -> None:
    class ToolResponse:
        def __init__(self, body: dict) -> None:
            self.body = body

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.body

    class ToolClient:
        calls = 0

        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, *args, **kwargs):
            ToolClient.calls += 1
            if ToolClient.calls == 1:
                return ToolResponse({"choices": [{"message": {"content": None, "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "search_products", "arguments": json.dumps({"query": "牛奶"}, ensure_ascii=False)}}]}}], "usage": {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25}})
            content = json.dumps({"intent": "product_search", "reply": "找到了牛奶。", "action": {"type": "product_search", "query": "牛奶"}, "needs_confirmation": False, "suggestions": []}, ensure_ascii=False)
            return ToolResponse({"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}})

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-returned")
    monkeypatch.setattr("app.assistant_service.httpx.AsyncClient", ToolClient)
    result = TestClient(create_app(tmp_path)).post("/api/v1/assistant/chat", json={"text": "帮我找牛奶", "conversation_id": "conversation-1", "history": [{"role": "user", "content": "我想买东西"}]}).json()["data"]
    assert result["provider"] == "deepseek"
    assert result["tool_calls"] == ["search_products"]
    assert result["action"]["product_ids"] == ["milk-001"]
    audit = json.loads((tmp_path / "assistant_audit.json").read_text(encoding="utf-8"))["items"][0]
    assert audit["tool_names"] == ["search_products"]

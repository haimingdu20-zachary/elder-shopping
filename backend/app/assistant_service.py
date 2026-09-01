from __future__ import annotations

import json
import os
import time
from typing import Any
from uuid import uuid4

import httpx

from .service import CommerceService
from .knowledge_service import KnowledgeService


class AssistantService:
    """DeepSeek-backed intent parsing with an explicit deterministic fallback."""

    ALLOWED_INTENTS = {"product_search", "order_list", "logistics_query", "knowledge_query", "after_sale_entry", "family_payment_entry", "unknown"}
    HIGH_RISK_INTENTS = {"after_sale_entry", "family_payment_entry"}
    ALLOWED_ACTIONS = {"product_search", "orders", "knowledge_search"}
    TOOL_DEFINITIONS = [
        {"type": "function", "function": {"name": "search_products", "description": "按关键词查询当前可购买商品。", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
        {"type": "function", "function": {"name": "list_orders", "description": "查询当前演示老人的订单摘要。", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
        {"type": "function", "function": {"name": "search_knowledge", "description": "查询退货、配送和家人协助说明。", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    ]

    def __init__(self, commerce: CommerceService, knowledge: KnowledgeService):
        self.commerce = commerce
        self.knowledge = knowledge
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        try:
            self.timeout_seconds = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "20"))
        except ValueError:
            self.timeout_seconds = 20.0

    async def chat(self, text: str, user_id: str = "demo-elder", history: list[dict[str, str]] | None = None, conversation_id: str | None = None) -> dict[str, Any]:
        if not self.api_key:
            result = self._with_meta(self._rule_chat(text, user_id), "rules")
            self._audit(result, conversation_id, [], None)
            return result
        try:
            result, tool_names = await self._deepseek_chat(text, history or [])
            result = self._with_meta(result, "deepseek")
            self._audit(result, conversation_id, tool_names, None)
            return result
        except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            fallback = self._with_meta(self._rule_chat(text, user_id), "rules_fallback")
            fallback["warning"] = "DEEPSEEK_UNAVAILABLE"
            self._audit(fallback, conversation_id, [], "DEEPSEEK_UNAVAILABLE")
            return fallback

    async def _deepseek_chat(self, text: str, history: list[dict[str, str]]) -> tuple[dict[str, Any], list[str]]:
        product_names = [item["name"] for item in self.commerce.list_products()]
        knowledge_context = self.knowledge.all_active()
        system_prompt = (
            "你是老人购物的意图解析器。只返回一个 JSON 对象，不要 Markdown。"
            "intent 只能是 product_search、order_list、logistics_query、knowledge_query、after_sale_entry、family_payment_entry、unknown。"
            "action.type 只能是 product_search 或 orders。不能执行付款、退款、改地址、确认收货。"
            "高风险意图 after_sale_entry 和 family_payment_entry 必须 needs_confirmation=true。"
            f"当前商品名称仅供匹配：{json.dumps(product_names, ensure_ascii=False)}。"
            f"可引用的本地知识只有：{json.dumps(knowledge_context, ensure_ascii=False)}。"
            "knowledge_query 的 action.type 必须是 knowledge_search，回答只能依据给出的本地知识。"
            "JSON 字段必须包含 intent、reply、action、needs_confirmation、suggestions。"
        )
        safe_history = [{"role": item.get("role"), "content": item.get("content", "").strip()} for item in history[-8:] if item.get("role") in {"user", "assistant"} and item.get("content", "").strip()][:8]
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}, *safe_history, {"role": "user", "content": text}]
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": self.TOOL_DEFINITIONS,
            "tool_choice": "auto",
            "thinking": {"type": "disabled"},
            "max_tokens": 400,
        }
        started = time.monotonic()
        tool_names: list[str] = []
        tool_arguments: dict[str, dict[str, Any]] = {}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json=payload)
            response.raise_for_status()
            body = response.json()
        message = body["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": tool_calls})
            for tool_call in tool_calls[:3]:
                function = tool_call.get("function") or {}
                tool_name = function.get("name")
                if tool_name not in {"search_products", "list_orders", "search_knowledge"}:
                    raise ValueError("Unapproved tool")
                arguments = json.loads(function.get("arguments") or "{}")
                tool_names.append(tool_name)
                tool_arguments[tool_name] = arguments
                tool_result = self._execute_readonly_tool(tool_name, arguments)
                messages.append({"role": "tool", "tool_call_id": tool_call.get("id", f"tool-{uuid4().hex[:8]}"), "content": json.dumps(tool_result, ensure_ascii=False)})
            final_payload = {"model": self.model, "messages": messages, "tools": self.TOOL_DEFINITIONS, "tool_choice": "none", "response_format": {"type": "json_object"}, "thinking": {"type": "disabled"}, "max_tokens": 400}
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                final_response = await client.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json=final_payload)
                final_response.raise_for_status()
                body = final_response.json()
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("DeepSeek content is not text")
        result = json.loads(content)
        normalized = self._normalize_model_result(result, tool_arguments)
        normalized["latency_ms"] = round((time.monotonic() - started) * 1000)
        usage = body.get("usage") or {}
        normalized["usage"] = {"prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0), "total_tokens": usage.get("total_tokens", 0)}
        normalized["tool_calls"] = tool_names
        return normalized, tool_names

    def _execute_readonly_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "search_products":
            query = str(arguments.get("query", "")).strip()
            if not query or len(query) > 80:
                raise ValueError("Invalid product query")
            return {"products": self.commerce.list_products(q=query)}
        if tool_name == "list_orders":
            return {"orders": self.commerce.orders()}
        if tool_name == "search_knowledge":
            query = str(arguments.get("query", "")).strip()
            if not query or len(query) > 200:
                raise ValueError("Invalid knowledge query")
            return {"sources": self.knowledge.search(query)}
        raise ValueError("Unapproved tool")

    def _audit(self, result: dict[str, Any], conversation_id: str | None, tool_names: list[str], error_code: str | None) -> None:
        try:
            records = self.commerce.store.read_items("assistant_audit.json", [])
            usage = result.get("usage") or {}
            records.insert(0, {"request_id": f"audit-{uuid4().hex[:12]}", "conversation_id": conversation_id, "provider": result.get("provider"), "model": result.get("model"), "intent": result.get("intent"), "tool_names": tool_names, "latency_ms": result.get("latency_ms"), "prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0), "total_tokens": usage.get("total_tokens", 0), "error_code": error_code, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            self.commerce.store.write_items("assistant_audit.json", records[:100])
        except Exception:
            return None

    def _normalize_model_result(self, result: Any, tool_arguments: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise ValueError("DeepSeek result is not an object")
        intent = result.get("intent")
        if intent not in self.ALLOWED_INTENTS:
            raise ValueError("Unknown intent")
        action = result.get("action")
        normalized_action: dict[str, Any] | None = None
        if isinstance(action, dict) and action.get("type") in self.ALLOWED_ACTIONS:
            if action["type"] == "product_search":
                query = str(action.get("query") or (tool_arguments or {}).get("search_products", {}).get("query", "")).strip()
                if not query:
                    raise ValueError("Product search has no query")
                products = self.commerce.list_products(q=query)
                normalized_action = {"type": "product_search", "query": query, "product_ids": [item["id"] for item in products]}
            elif action["type"] == "knowledge_search":
                query = str(action.get("query") or (tool_arguments or {}).get("search_knowledge", {}).get("query", "")).strip()
                if not query:
                    raise ValueError("Knowledge search has no query")
                documents = self.knowledge.search(query)
                normalized_action = {"type": "knowledge_search", "query": query, "sources": [{"source_id": item["source_id"], "title": item["title"]} for item in documents]}
                if intent == "knowledge_query":
                    result["reply"] = "根据平台说明：" + " ".join(item["content"] for item in documents) if documents else "暂时没有找到对应说明，建议联系客服确认。"
            else:
                normalized_action = {"type": "orders"}
                if action.get("filter") in {"delivered", "pending_payment", "shipping"}:
                    normalized_action["filter"] = action["filter"]
                normalized_action["order_count"] = len(self.commerce.orders())
        needs_confirmation = bool(result.get("needs_confirmation")) or intent in self.HIGH_RISK_INTENTS
        suggestions = result.get("suggestions")
        if not isinstance(suggestions, list):
            suggestions = ["查我的订单", "查物流", "申请售后"]
        return {"intent": intent, "reply": str(result.get("reply") or "我已理解您的意思，请按页面提示继续。"), "action": normalized_action, "needs_confirmation": needs_confirmation, "suggestions": [str(item) for item in suggestions[:3]]}

    def _rule_chat(self, text: str, user_id: str) -> dict[str, Any]:
        normalized = "".join(text.strip().lower().split())
        if any(word in normalized for word in ("规则", "怎么退", "怎么申请", "能不能退", "怎么配送", "怎么协助", "如何代付")):
            documents = self.knowledge.search(text)
            if documents:
                sources = [{"source_id": item["source_id"], "title": item["title"]} for item in documents]
                return self._result("knowledge_query", "根据平台说明：" + " ".join(item["content"] for item in documents), {"type": "knowledge_search", "query": text, "sources": sources}, False)
            return self._result("knowledge_query", "暂时没有找到对应说明，建议联系客服确认。", {"type": "knowledge_search", "query": text, "sources": []}, False)
        if any(word in normalized for word in ("退货", "退款", "售后")):
            return self._result("after_sale_entry", "请先打开订单，选择一笔已送达订单，再确认售后信息。", {"type": "orders", "filter": "delivered"}, True)
        if any(word in normalized for word in ("家人付款", "家人代付", "女儿付款", "帮我付款")):
            return self._result("family_payment_entry", "请打开待付款订单，再生成家人代付链接。", {"type": "orders", "filter": "pending_payment"}, True)
        if any(word in normalized for word in ("物流", "快递", "送到哪", "到哪了")):
            return self._result("logistics_query", "我可以帮您查看物流，请先选择要查看的订单。", {"type": "orders", "filter": "shipping"}, False)
        if any(word in normalized for word in ("订单", "买过什么", "我的订单")):
            return self._result("order_list", "我为您打开订单列表，您可以查看每笔订单的状态。", {"type": "orders"}, False)
        query = self._product_query(text)
        if any(word in normalized for word in ("商品", "买", "找", "看看", "有没有", "需要", "查")) and query:
            products = self.commerce.list_products(q=query)
            if products:
                return self._result("product_search", f"我找到了 {len(products)} 件和“{query}”相关的商品。", {"type": "product_search", "query": query, "product_ids": [item["id"] for item in products]}, False)
            return self._result("product_search", f"暂时没有找到“{query}”，您可以换个说法试试。", {"type": "product_search", "query": query, "product_ids": []}, False)
        return self._result("unknown", "我还没听懂。您可以说：查牛奶、查订单、查物流、申请售后或让家人付款。", None, False)

    @staticmethod
    def _product_query(text: str) -> str:
        query = text.strip()
        for phrase in ("我想买", "我要买", "帮我找", "帮我看看", "有没有", "查一下", "找一下", "看看", "查", "找", "买"):
            query = query.replace(phrase, "")
        for suffix in ("商品", "好吗", "呢", "吧"):
            query = query.replace(suffix, "")
        return query.strip()

    @staticmethod
    def _result(intent: str, reply: str, action: dict[str, Any] | None, needs_confirmation: bool) -> dict[str, Any]:
        return {"intent": intent, "reply": reply, "action": action, "needs_confirmation": needs_confirmation, "suggestions": ["查我的订单", "查物流", "申请售后"]}

    def _with_meta(self, result: dict[str, Any], provider: str) -> dict[str, Any]:
        result = dict(result)
        result["provider"] = provider
        if provider == "deepseek":
            result["model"] = self.model
        return result

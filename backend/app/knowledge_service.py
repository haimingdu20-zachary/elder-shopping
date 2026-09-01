from __future__ import annotations

from typing import Any

from .storage import JsonStore


def seed_knowledge() -> list[dict[str, Any]]:
    return [
        {"source_id": "faq-after-sale", "title": "退货退款怎么申请", "keywords": ["退货", "退款", "售后", "申请"], "content": "打开已送达订单，点击申请退款/退货，选择处理方式和原因，确认退款金额与去向后提交。原型阶段只展示模拟状态，不代表真实审核和退款到账。", "version": "v1", "status": "active"},
        {"source_id": "faq-delivery", "title": "配送和物流说明", "keywords": ["配送", "物流", "快递", "送到", "发货"], "content": "商品详情页会显示预计送达时间；付款后订单进入待发货，配送中的订单会显示模拟物流提示。原型阶段不连接真实物流公司。", "version": "v1", "status": "active"},
        {"source_id": "faq-family", "title": "家人协助说明", "keywords": ["家人", "代付", "代买", "协助", "女儿"], "content": "老人可以从待付款订单生成家人代付链接，家人在绑定关系和授权范围内查看订单并完成模拟代付。家人不能修改老人的地址或直接操作真实支付。", "version": "v1", "status": "active"},
    ]


class KnowledgeService:
    def __init__(self, store: JsonStore):
        self.store = store

    def _items(self) -> list[dict[str, Any]]:
        return self.store.read_items("knowledge.json", seed_knowledge())

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        normalized = query.strip().lower()
        if not normalized:
            return []
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in self._items():
            if item.get("status") != "active":
                continue
            haystack = " ".join([item["title"], item["content"], *item.get("keywords", [])]).lower()
            score = sum(1 for token in item.get("keywords", []) if token.lower() in normalized)
            if normalized in haystack:
                score += 2
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [{"source_id": item["source_id"], "title": item["title"], "content": item["content"], "version": item["version"]} for _, item in scored[:limit]]

    def all_active(self) -> list[dict[str, Any]]:
        return [{"source_id": item["source_id"], "title": item["title"], "content": item["content"], "version": item["version"]} for item in self._items() if item.get("status") == "active"]

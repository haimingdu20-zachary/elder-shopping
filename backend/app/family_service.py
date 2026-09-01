from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select

from .family_db import AssistRequest, FamilyDatabase, FamilyLink
from .service import AppError, CommerceService, now_iso


KIND_LABELS = {"payment": "家人代付", "after_sale": "家人协助售后"}
REQUEST_STATUS_LABELS = {"pending": "待处理", "completed": "已完成", "cancelled": "已取消"}


class FamilyService:
    def __init__(self, db: FamilyDatabase, commerce: CommerceService):
        self.db = db
        self.commerce = commerce

    def _link(self, family_user_id: str, elder_user_id: str = "demo-elder") -> FamilyLink:
        with self.db.SessionLocal() as session:
            link = session.scalar(select(FamilyLink).where(
                FamilyLink.family_user_id == family_user_id,
                FamilyLink.elder_user_id == elder_user_id,
                FamilyLink.status == "active",
            ))
            if link is None:
                raise AppError("FAMILY_ACCESS_DENIED", "当前家人账号没有这项协助权限。", 403)
            return link

    def _require_permission(self, family_user_id: str, permission: str, elder_user_id: str = "demo-elder") -> FamilyLink:
        link = self._link(family_user_id, elder_user_id)
        if permission not in self.db.permissions(link):
            raise AppError("FAMILY_PERMISSION_DENIED", "当前家人账号没有这项协助权限。", 403)
        return link

    def _with_order(self, record: dict[str, Any]) -> dict[str, Any]:
        result = dict(record)
        result["kind_label"] = KIND_LABELS.get(record["kind"], record["kind"])
        result["status_label"] = REQUEST_STATUS_LABELS.get(record["status"], record["status"])
        if record.get("order_id"):
            result["order"] = self.commerce.order_detail(record["order_id"])
            result["share_url"] = f"/family/requests/{record['id']}"
        return result

    def members(self, elder_user_id: str = "demo-elder") -> list[dict[str, Any]]:
        with self.db.SessionLocal() as session:
            links = list(session.scalars(select(FamilyLink).where(FamilyLink.elder_user_id == elder_user_id, FamilyLink.status == "active")))
            return [{"family_user_id": link.family_user_id, "relationship": link.relationship, "permissions": self.db.permissions(link), "status": link.status} for link in links]

    def orders(self, family_user_id: str) -> list[dict[str, Any]]:
        self._require_permission(family_user_id, "view_orders")
        result = []
        for order in self.commerce.orders():
            item = dict(order)
            item["elder_user_id"] = "demo-elder"
            item["created_by_user_id"] = self._created_by(order["id"])
            result.append(item)
        return result

    def _created_by(self, order_id: str) -> str:
        try:
            return self.commerce.order_detail(order_id).get("created_by_user_id", "demo-elder")
        except AppError:
            return "demo-elder"

    def order_detail(self, order_id: str, family_user_id: str) -> dict[str, Any]:
        self._require_permission(family_user_id, "view_orders")
        detail = self.commerce.order_detail(order_id)
        detail["elder_user_id"] = "demo-elder"
        detail["created_by_user_id"] = detail.get("created_by_user_id", "demo-elder")
        return detail

    def create_order(self, family_user_id: str, items: list[dict[str, Any]], address_id: str, idempotency_key: str) -> dict[str, Any]:
        self._require_permission(family_user_id, "assist_order")
        return self.commerce.create_order_draft(items, address_id, idempotency_key, created_by_user_id=family_user_id)

    def create_payment_request(self, elder_user_id: str, order_id: str, family_user_id: str, note: str) -> dict[str, Any]:
        self._require_permission(family_user_id, "pay", elder_user_id)
        order = self.commerce.order_detail(order_id)
        if order["status"] != "pending_payment":
            raise AppError("PAYMENT_NOT_ALLOWED", "这个订单当前不需要家人代付。")
        with self.db.SessionLocal() as session:
            existing = session.scalar(select(AssistRequest).where(
                AssistRequest.elder_user_id == elder_user_id,
                AssistRequest.family_user_id == family_user_id,
                AssistRequest.order_id == order_id,
                AssistRequest.kind == "payment",
                AssistRequest.status == "pending",
            ))
            if existing:
                return self._with_order(self.db.request_dict(existing))
            timestamp = now_iso()
            record = AssistRequest(id=f"assist-{uuid4().hex[:10]}", elder_user_id=elder_user_id, family_user_id=family_user_id, kind="payment", order_id=order_id, status="pending", note=note, created_at=timestamp, updated_at=timestamp)
            session.add(record)
            session.commit()
            return self._with_order(self.db.request_dict(record))

    def requests(self, family_user_id: str) -> list[dict[str, Any]]:
        self._require_permission(family_user_id, "view_orders")
        with self.db.SessionLocal() as session:
            records = list(session.scalars(select(AssistRequest).where(AssistRequest.family_user_id == family_user_id).order_by(AssistRequest.created_at.desc())))
            return [self._with_order(self.db.request_dict(record)) for record in records]

    def request_detail(self, request_id: str, family_user_id: str) -> dict[str, Any]:
        self._require_permission(family_user_id, "view_orders")
        with self.db.SessionLocal() as session:
            record = session.get(AssistRequest, request_id)
            if record is None or record.family_user_id != family_user_id:
                raise AppError("ASSIST_REQUEST_NOT_FOUND", "没有找到这条家人协助请求。", 404)
            return self._with_order(self.db.request_dict(record))

    def confirm_payment(self, request_id: str, family_user_id: str) -> dict[str, Any]:
        self._require_permission(family_user_id, "pay")
        with self.db.SessionLocal() as session:
            record = session.get(AssistRequest, request_id)
            if record is None or record.family_user_id != family_user_id or record.kind != "payment":
                raise AppError("ASSIST_REQUEST_NOT_FOUND", "没有找到这条代付请求。", 404)
            if record.status == "completed":
                return self._with_order(self.db.request_dict(record))
            if record.status != "pending":
                raise AppError("ASSIST_REQUEST_NOT_ALLOWED", "这条协助请求当前不能确认。")
            payment = self.commerce.simulate_payment(record.order_id or "", "success", f"family-payment-{record.id}")
            record.status = "completed"
            record.completed_at = now_iso()
            record.updated_at = record.completed_at
            session.commit()
            result = self.db.request_dict(record)
            result["order"] = payment["order"]
            return self._with_order(result)

    def cancel_request(self, request_id: str, family_user_id: str) -> dict[str, Any]:
        self._require_permission(family_user_id, "view_orders")
        with self.db.SessionLocal() as session:
            record = session.get(AssistRequest, request_id)
            if record is None or record.family_user_id != family_user_id:
                raise AppError("ASSIST_REQUEST_NOT_FOUND", "没有找到这条家人协助请求。", 404)
            if record.status == "cancelled":
                return self._with_order(self.db.request_dict(record))
            if record.status != "pending":
                raise AppError("ASSIST_REQUEST_NOT_ALLOWED", "这条协助请求当前不能取消。")
            record.status = "cancelled"
            record.updated_at = now_iso()
            session.commit()
            return self._with_order(self.db.request_dict(record))

    def create_after_sale_request(self, family_user_id: str, elder_user_id: str, order_id: str, note: str) -> dict[str, Any]:
        self._require_permission(family_user_id, "assist_after_sale", elder_user_id)
        order = self.commerce.order_detail(order_id)
        if order["status"] not in {"delivered", "after_sale"}:
            raise AppError("AFTER_SALE_NOT_ALLOWED", "只有已送达或售后中的订单可以请求家人协助。")
        with self.db.SessionLocal() as session:
            existing = session.scalar(select(AssistRequest).where(
                AssistRequest.elder_user_id == elder_user_id,
                AssistRequest.family_user_id == family_user_id,
                AssistRequest.order_id == order_id,
                AssistRequest.kind == "after_sale",
                AssistRequest.status == "pending",
            ))
            if existing:
                return self._with_order(self.db.request_dict(existing))
            timestamp = now_iso()
            record = AssistRequest(id=f"assist-{uuid4().hex[:10]}", elder_user_id=elder_user_id, family_user_id=family_user_id, kind="after_sale", order_id=order_id, status="pending", note=note, created_at=timestamp, updated_at=timestamp)
            session.add(record)
            session.commit()
            return self._with_order(self.db.request_dict(record))

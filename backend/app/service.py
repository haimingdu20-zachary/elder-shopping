from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import uuid4

from .storage import JsonStore


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def money(value: Decimal | int | float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


STATUS_LABELS = {
    "pending_payment": "待付款",
    "paid_pending_shipment": "已付款/待发货",
    "shipping": "配送中",
    "delivered": "已送达",
    "completed": "已完成",
    "after_sale": "售后中",
    "after_sale_completed": "售后完成",
}


class CommerceService:
    def __init__(self, store: JsonStore, user_id: str = "demo-elder", ensure_seed: bool = True):
        self.store = store
        self.user_id = user_id
        if ensure_seed:
            self._ensure_seed_data()

    def for_user(self, user_id: str) -> "CommerceService":
        return CommerceService(self.store, user_id, ensure_seed=False)

    def _ensure_seed_data(self) -> None:
        self.store.read_items("products.json", seed_products())
        self.store.read_items("addresses.json", seed_addresses())
        self.store.read_items("carts.json", [{"user_id": self.user_id, "items": []}])
        self.store.read_items("orders.json", seed_orders(self.user_id))
        self.store.read_items("after_sales.json", seed_after_sales(self.user_id))

    def _products(self) -> list[dict[str, Any]]:
        return self.store.read_items("products.json", seed_products())

    def _addresses(self) -> list[dict[str, Any]]:
        return self.store.read_items("addresses.json", seed_addresses())

    def _orders(self) -> list[dict[str, Any]]:
        return self.store.read_items("orders.json", seed_orders(self.user_id))

    def _save_orders(self, orders: list[dict[str, Any]]) -> None:
        self.store.write_items("orders.json", orders)

    def _after_sales(self) -> list[dict[str, Any]]:
        return self.store.read_items("after_sales.json", seed_after_sales(self.user_id))

    def _save_after_sales(self, records: list[dict[str, Any]]) -> None:
        self.store.write_items("after_sales.json", records)

    def categories(self) -> list[dict[str, str]]:
        products = self._products()
        categories: dict[str, str] = {}
        for product in products:
            if product["status"] == "active":
                categories[product["category_id"]] = product["category_name"]
        return [{"id": key, "name": name} for key, name in categories.items()]

    def list_products(self, q: str | None = None, category_id: str | None = None, featured: bool | None = None) -> list[dict[str, Any]]:
        if q and len(q) > 80:
            raise AppError("VALIDATION_ERROR", "搜索内容太长了，请少输入一些。")
        query = (q or "").strip().lower()
        result = []
        for product in self._products():
            if product["status"] != "active":
                continue
            haystack = " ".join([product["name"], product["specification"], product["category_name"]]).lower()
            if query and query not in haystack:
                continue
            if category_id and product["category_id"] != category_id:
                continue
            if featured is True and not product["is_featured"]:
                continue
            result.append(self._product_summary(product))
        return result

    def product(self, product_id: str) -> dict[str, Any]:
        for product in self._products():
            if product["id"] == product_id and product["status"] == "active":
                return deepcopy(product)
        raise AppError("PRODUCT_NOT_FOUND", "没有找到这个商品。", 404)

    def addresses(self) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._addresses() if item["user_id"] == self.user_id]

    def _product_summary(self, product: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": product["id"],
            "name": product["name"],
            "image_url": product["image_url"],
            "price": product["price"],
            "unit_label": product["unit_label"],
            "category_id": product["category_id"],
            "category_name": product["category_name"],
            "stock": product["stock"],
            "stock_text": "有货" if product["stock"] > 0 else "暂时缺货",
            "estimated_delivery_text": product["estimated_delivery_text"],
            "is_featured": product["is_featured"],
        }

    def _cart_record(self) -> dict[str, Any]:
        records = self.store.read_items("carts.json", [{"user_id": self.user_id, "items": []}])
        for record in records:
            if record.get("user_id") == self.user_id:
                return record
        record = {"user_id": self.user_id, "items": []}
        records.append(record)
        self.store.write_items("carts.json", records)
        return record

    def cart(self) -> dict[str, Any]:
        record = self._cart_record()
        return self._cart_view(record["items"])

    def update_cart(self, product_id: str, quantity: int) -> dict[str, Any]:
        product = self.product(product_id)
        if quantity > product["stock"]:
            raise AppError("INVALID_QUANTITY", "购买数量超过当前模拟库存。")
        records = self.store.read_items("carts.json", [{"user_id": self.user_id, "items": []}])
        record = next((item for item in records if item.get("user_id") == self.user_id), None)
        if record is None:
            record = {"user_id": self.user_id, "items": []}
            records.append(record)
        record["items"] = [item for item in record["items"] if item["product_id"] != product_id]
        if quantity > 0:
            record["items"].append({"product_id": product_id, "quantity": quantity})
        record["updated_at"] = now_iso()
        self.store.write_items("carts.json", records)
        return self._cart_view(record["items"])

    def _cart_view(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        viewed = []
        subtotal = Decimal("0")
        for item in items:
            product = self.product(item["product_id"])
            item_total = Decimal(str(product["price"])) * item["quantity"]
            subtotal += item_total
            viewed.append({"product": self._product_summary(product), "quantity": item["quantity"], "item_total": money(item_total)})
        shipping = Decimal("0") if subtotal >= Decimal("99") or subtotal == 0 else Decimal("8")
        return {"items": viewed, "items_amount": money(subtotal), "shipping_fee": money(shipping), "total_amount": money(subtotal + shipping)}

    def create_order_draft(self, items: list[dict[str, Any]], address_id: str, idempotency_key: str, created_by_user_id: str | None = None) -> dict[str, Any]:
        if not items:
            raise AppError("CART_EMPTY", "购物车还是空的，请先选择商品。")
        orders = self._orders()
        existing = next((order for order in orders if order.get("idempotency_key") == idempotency_key), None)
        if existing:
            return self.order_detail(existing["id"])
        address = next((item for item in self._addresses() if item["id"] == address_id and item["user_id"] == self.user_id), None)
        if not address:
            raise AppError("ADDRESS_NOT_FOUND", "没有找到这个收货地址。")
        product_map = {product["id"]: product for product in self._products()}
        snapshots = []
        subtotal = Decimal("0")
        for requested in items:
            product = product_map.get(requested["product_id"])
            if not product or product["status"] != "active":
                raise AppError("PRODUCT_NOT_FOUND", "购物车里有商品已经找不到了。")
            if requested["quantity"] > product["stock"]:
                raise AppError("INVALID_QUANTITY", f"{product['name']} 的数量超过模拟库存。")
            item_total = Decimal(str(product["price"])) * requested["quantity"]
            subtotal += item_total
            snapshots.append({"product_id": product["id"], "name": product["name"], "image_url": product["image_url"], "price": product["price"], "unit_label": product["unit_label"], "quantity": requested["quantity"], "item_total": money(item_total)})
        shipping = Decimal("0") if subtotal >= Decimal("99") else Decimal("8")
        order = {
            "id": f"order-{uuid4().hex[:10]}",
            "user_id": self.user_id,
            "items": snapshots,
            "items_amount": money(subtotal),
            "shipping_fee": money(shipping),
            "total_amount": money(subtotal + shipping),
            "address_snapshot": deepcopy(address),
            "payment_status": "pending",
            "delivery_status": "not_shipped",
            "after_sale_status": "not_started",
            "status": "pending_payment",
            "status_label": STATUS_LABELS["pending_payment"],
            "logistics_text": "付款后我们会尽快安排发货。",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "idempotency_key": idempotency_key,
        }
        if created_by_user_id:
            order["created_by_user_id"] = created_by_user_id
        orders.insert(0, order)
        self._save_orders(orders)
        return self.order_detail(order["id"])

    def orders(self) -> list[dict[str, Any]]:
        return [self._order_summary(order) for order in self._orders() if order.get("user_id") == self.user_id]

    def order_detail(self, order_id: str) -> dict[str, Any]:
        order = next((item for item in self._orders() if item["id"] == order_id and item.get("user_id") == self.user_id), None)
        if not order:
            raise AppError("ORDER_NOT_FOUND", "没有找到这个订单。", 404)
        return deepcopy(self._order_detail(order))

    def _order_summary(self, order: dict[str, Any]) -> dict[str, Any]:
        return {"id": order["id"], "items": order["items"], "total_amount": order["total_amount"], "status": order["status"], "status_label": STATUS_LABELS.get(order["status"], order["status"]), "next_action": self._next_action(order), "created_at": order["created_at"], "updated_at": order["updated_at"]}

    def _order_detail(self, order: dict[str, Any]) -> dict[str, Any]:
        detail = deepcopy(order)
        detail["status_label"] = STATUS_LABELS.get(order["status"], order["status"])
        detail["next_action"] = self._next_action(order)
        detail["can_apply_after_sale"] = order["status"] == "delivered"
        detail["can_confirm_receipt"] = order["status"] == "delivered"
        detail["can_pay"] = order["status"] == "pending_payment"
        return detail

    def _next_action(self, order: dict[str, Any]) -> str:
        return {"pending_payment": "继续付款", "shipping": "查看物流", "delivered": "确认收货或申请售后", "after_sale": "查看售后进度", "completed": "再次购买"}.get(order["status"], "查看订单")

    def simulate_payment(self, order_id: str, result: str, idempotency_key: str) -> dict[str, Any]:
        orders = self._orders()
        order = next((item for item in orders if item["id"] == order_id and item.get("user_id") == self.user_id), None)
        if not order:
            raise AppError("ORDER_NOT_FOUND", "没有找到这个订单。", 404)
        if order.get("payment_idempotency_key") == idempotency_key:
            return {"order": self._order_detail(order), "message": order.get("last_payment_message", "付款状态已确认。")}
        if order["status"] != "pending_payment":
            raise AppError("PAYMENT_NOT_ALLOWED", "这个订单当前不需要付款。")
        messages = {"success": "模拟付款成功，订单已经进入待发货。", "failed": "模拟付款失败，订单仍保留在待付款。", "cancelled": "您已取消付款，订单仍保留在待付款。"}
        order["payment_idempotency_key"] = idempotency_key
        order["last_payment_message"] = messages[result]
        if result == "success":
            order["status"] = "paid_pending_shipment"
            order["payment_status"] = "paid"
            order["logistics_text"] = "订单已付款，等待商家发货。"
        order["updated_at"] = now_iso()
        self._save_orders(orders)
        return {"order": self._order_detail(order), "message": messages[result]}

    def confirm_receipt(self, order_id: str) -> dict[str, Any]:
        orders = self._orders()
        order = next((item for item in orders if item["id"] == order_id and item.get("user_id") == self.user_id), None)
        if not order:
            raise AppError("ORDER_NOT_FOUND", "没有找到这个订单。", 404)
        if order["status"] != "delivered":
            raise AppError("INVALID_ORDER_STATE", "只有已送达的订单可以确认收货。")
        order["status"] = "completed"
        order["delivery_status"] = "completed"
        order["status_label"] = STATUS_LABELS["completed"]
        order["updated_at"] = now_iso()
        self._save_orders(orders)
        return self._order_detail(order)

    def create_after_sale_draft(self, order_id: str, sale_type: str, reason: str, return_method: str, idempotency_key: str) -> dict[str, Any]:
        orders = self._orders()
        order = next((item for item in orders if item["id"] == order_id and item.get("user_id") == self.user_id), None)
        if not order:
            raise AppError("ORDER_NOT_FOUND", "没有找到这个订单。", 404)
        if order["status"] != "delivered":
            raise AppError("AFTER_SALE_NOT_ALLOWED", "只有已送达的订单可以申请售后。")
        records = self._after_sales()
        existing = next((item for item in records if item.get("idempotency_key") == idempotency_key), None)
        if existing:
            return deepcopy(existing)
        record = {"id": f"after-sale-{uuid4().hex[:10]}", "order_id": order_id, "user_id": self.user_id, "type": sale_type, "reason": reason, "refund_amount": order["total_amount"], "refund_destination": "原支付方式（模拟）", "return_method": return_method, "status": "draft", "status_label": "售后草稿", "created_at": now_iso(), "updated_at": now_iso(), "idempotency_key": idempotency_key}
        records.insert(0, record)
        self._save_after_sales(records)
        return deepcopy(record)

    def submit_after_sale(self, after_sale_id: str, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise AppError("VALIDATION_ERROR", "请确认售后信息后再提交。")
        records = self._after_sales()
        record = next((item for item in records if item["id"] == after_sale_id and item.get("user_id") == self.user_id), None)
        if not record:
            raise AppError("AFTER_SALE_NOT_FOUND", "没有找到这条售后申请。", 404)
        if record["status"] == "submitted":
            return deepcopy(record)
        if record["status"] != "draft":
            raise AppError("INVALID_ORDER_STATE", "这条售后申请当前不能提交。")
        record["status"] = "submitted"
        record["status_label"] = "售后申请已提交"
        record["updated_at"] = now_iso()
        self._save_after_sales(records)
        orders = self._orders()
        order = next((item for item in orders if item["id"] == record["order_id"]), None)
        if order:
            order["status"] = "after_sale"
            order["after_sale_status"] = "processing"
            order["updated_at"] = now_iso()
            self._save_orders(orders)
        return deepcopy(record)

    def after_sale(self, after_sale_id: str) -> dict[str, Any]:
        record = next((item for item in self._after_sales() if item["id"] == after_sale_id and item.get("user_id") == self.user_id), None)
        if not record:
            raise AppError("AFTER_SALE_NOT_FOUND", "没有找到这条售后申请。", 404)
        return deepcopy(record)


def seed_products() -> list[dict[str, Any]]:
    return [
        {"id": "milk-001", "name": "伊利纯牛奶", "specification": "250ml × 24盒", "unit_label": "箱", "price": 98, "image_url": "/products/milk.svg", "category_id": "food", "category_name": "食品饮料", "stock": 20, "delivery_area": "上海市大部分地区", "estimated_delivery_text": "预计明天送到", "return_policy": "支持7天无理由退货", "is_featured": True, "status": "active"},
        {"id": "rice-001", "name": "东北大米", "specification": "5kg 袋装", "unit_label": "袋", "price": 59, "image_url": "/products/rice.svg", "category_id": "food", "category_name": "食品饮料", "stock": 30, "delivery_area": "上海市大部分地区", "estimated_delivery_text": "预计后天送到", "return_policy": "支持7天无理由退货", "is_featured": True, "status": "active"},
        {"id": "oatmeal-001", "name": "营养燕麦片", "specification": "800g 罐装", "unit_label": "罐", "price": 36, "image_url": "/products/oatmeal.svg", "category_id": "food", "category_name": "食品饮料", "stock": 15, "delivery_area": "上海市大部分地区", "estimated_delivery_text": "预计明天送到", "return_policy": "支持7天无理由退货", "is_featured": False, "status": "active"},
        {"id": "paper-001", "name": "柔软抽纸", "specification": "3层 × 24包", "unit_label": "提", "price": 42, "image_url": "/products/paper.svg", "category_id": "daily", "category_name": "日用生活", "stock": 40, "delivery_area": "上海市大部分地区", "estimated_delivery_text": "预计明天送到", "return_policy": "支持7天无理由退货", "is_featured": True, "status": "active"},
        {"id": "soap-001", "name": "温和洗衣液", "specification": "3kg 家庭装", "unit_label": "瓶", "price": 45, "image_url": "/products/soap.svg", "category_id": "daily", "category_name": "日用生活", "stock": 18, "delivery_area": "上海市大部分地区", "estimated_delivery_text": "预计后天送到", "return_policy": "支持7天无理由退货", "is_featured": False, "status": "active"},
        {"id": "tea-001", "name": "清香绿茶", "specification": "250g 罐装", "unit_label": "罐", "price": 68, "image_url": "/products/tea.svg", "category_id": "food", "category_name": "食品饮料", "stock": 12, "delivery_area": "上海市大部分地区", "estimated_delivery_text": "预计明天送到", "return_policy": "支持7天无理由退货", "is_featured": False, "status": "active"},
    ]


def seed_addresses() -> list[dict[str, Any]]:
    return [
        {"id": "address-001", "user_id": "demo-elder", "name": "王阿姨", "phone": "138****2688", "full_address": "上海市浦东新区世纪大道 100 号", "is_default": True},
        {"id": "address-002", "user_id": "demo-elder", "name": "王阿姨", "phone": "138****2688", "full_address": "上海市浦东新区丁香路 200 号", "is_default": False},
    ]


def seed_orders(user_id: str) -> list[dict[str, Any]]:
    products = {item["id"]: item for item in seed_products()}
    def snapshot(product_id: str, quantity: int) -> dict[str, Any]:
        product = products[product_id]
        return {"product_id": product_id, "name": product["name"], "image_url": product["image_url"], "price": product["price"], "unit_label": product["unit_label"], "quantity": quantity, "item_total": money(Decimal(str(product["price"])) * quantity)}
    return [
        {"id": "order-demo-pending", "user_id": user_id, "items": [snapshot("paper-001", 1)], "items_amount": 42, "shipping_fee": 8, "total_amount": 50, "address_snapshot": seed_addresses()[0], "payment_status": "pending", "delivery_status": "not_shipped", "after_sale_status": "not_started", "status": "pending_payment", "logistics_text": "付款后我们会尽快安排发货。", "created_at": "2026-08-30T09:00:00+08:00", "updated_at": "2026-08-30T09:00:00+08:00", "idempotency_key": "seed-pending"},
        {"id": "order-demo-shipping", "user_id": user_id, "items": [snapshot("rice-001", 1)], "items_amount": 59, "shipping_fee": 8, "total_amount": 67, "address_snapshot": seed_addresses()[0], "payment_status": "paid", "delivery_status": "shipping", "after_sale_status": "not_started", "status": "shipping", "logistics_text": "包裹正在配送中，预计今天送到。", "created_at": "2026-08-28T09:00:00+08:00", "updated_at": "2026-08-30T10:00:00+08:00", "idempotency_key": "seed-shipping"},
        {"id": "order-demo-delivered", "user_id": user_id, "items": [snapshot("milk-001", 1)], "items_amount": 98, "shipping_fee": 0, "total_amount": 98, "address_snapshot": seed_addresses()[0], "payment_status": "paid", "delivery_status": "delivered", "after_sale_status": "not_started", "status": "delivered", "logistics_text": "包裹已送达，请您检查商品。", "created_at": "2026-08-25T09:00:00+08:00", "updated_at": "2026-08-27T16:00:00+08:00", "idempotency_key": "seed-delivered"},
        {"id": "order-demo-after-sale", "user_id": user_id, "items": [snapshot("oatmeal-001", 1)], "items_amount": 36, "shipping_fee": 8, "total_amount": 44, "address_snapshot": seed_addresses()[0], "payment_status": "paid", "delivery_status": "delivered", "after_sale_status": "processing", "status": "after_sale", "logistics_text": "售后申请处理中，客服会继续跟进。", "created_at": "2026-08-20T09:00:00+08:00", "updated_at": "2026-08-23T14:00:00+08:00", "idempotency_key": "seed-after-sale"},
    ]


def seed_after_sales(user_id: str) -> list[dict[str, Any]]:
    return [{"id": "after-sale-demo", "order_id": "order-demo-after-sale", "user_id": user_id, "type": "return_and_refund", "reason": "商品不需要了", "refund_amount": 44, "refund_destination": "原支付方式（模拟）", "return_method": "pickup", "status": "submitted", "status_label": "售后申请已提交", "created_at": "2026-08-21T09:00:00+08:00", "updated_at": "2026-08-23T14:00:00+08:00", "idempotency_key": "seed-after-sale-request"}]

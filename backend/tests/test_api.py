from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path))


def test_products_and_categories(tmp_path: Path) -> None:
    api = client(tmp_path)
    assert api.get("/api/v1/categories").status_code == 200
    products = api.get("/api/v1/products", params={"q": "牛奶"}).json()["data"]
    assert products[0]["name"] == "伊利纯牛奶"
    assert api.get("/api/v1/products/nope").json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_cart_order_payment_and_recovery(tmp_path: Path) -> None:
    api = client(tmp_path)
    updated = api.put("/api/v1/cart/items", json={"product_id": "milk-001", "quantity": 2})
    assert updated.status_code == 200
    assert updated.json()["data"]["total_amount"] == 196.0
    payload = {"items": [{"product_id": "milk-001", "quantity": 2}], "address_id": "address-001", "idempotency_key": "order-key-123"}
    created = api.post("/api/v1/orders/drafts", json=payload).json()["data"]
    order_id = created["id"]
    duplicate = api.post("/api/v1/orders/drafts", json=payload).json()["data"]
    assert duplicate["id"] == order_id
    failed = api.post(f"/api/v1/orders/{order_id}/simulate-payment", json={"result": "failed", "idempotency_key": "pay-key-123"}).json()["data"]
    assert failed["order"]["status"] == "pending_payment"
    success = api.post(f"/api/v1/orders/{order_id}/simulate-payment", json={"result": "success", "idempotency_key": "pay-key-456"}).json()["data"]
    assert success["order"]["status"] == "paid_pending_shipment"
    assert api.get(f"/api/v1/orders/{order_id}").json()["data"]["status"] == "paid_pending_shipment"


def test_after_sale_confirmation_and_errors(tmp_path: Path) -> None:
    api = client(tmp_path)
    invalid = api.post("/api/v1/after-sales/drafts", json={"order_id": "order-demo-shipping", "type": "return_and_refund", "reason": "商品不需要了", "return_method": "pickup", "idempotency_key": "after-key-123"})
    assert invalid.json()["error"]["code"] == "AFTER_SALE_NOT_ALLOWED"
    draft = api.post("/api/v1/after-sales/drafts", json={"order_id": "order-demo-delivered", "type": "return_and_refund", "reason": "商品不需要了", "return_method": "pickup", "idempotency_key": "after-key-123"}).json()["data"]
    not_confirmed = api.post(f"/api/v1/after-sales/{draft['id']}/submit", json={"confirm": False})
    assert not_confirmed.json()["error"]["code"] == "VALIDATION_ERROR"
    submitted = api.post(f"/api/v1/after-sales/{draft['id']}/submit", json={"confirm": True}).json()["data"]
    assert submitted["status"] == "submitted"
    assert api.get("/api/v1/orders/order-demo-delivered").json()["data"]["status"] == "after_sale"


def test_json_data_survives_new_app(tmp_path: Path) -> None:
    first = client(tmp_path)
    first.put("/api/v1/cart/items", json={"product_id": "paper-001", "quantity": 1})
    created = first.post("/api/v1/orders/drafts", json={"items": [{"product_id": "paper-001", "quantity": 1}], "address_id": "address-001", "idempotency_key": "persist-key-123"}).json()["data"]
    second = client(tmp_path)
    orders = second.get("/api/v1/orders").json()["data"]
    assert any(order["id"] == created["id"] for order in orders)
    assert (tmp_path / "orders.json").exists()

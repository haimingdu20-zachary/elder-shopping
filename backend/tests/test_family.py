from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path))


def test_family_binding_and_order_visibility(tmp_path: Path) -> None:
    api = client(tmp_path)
    members = api.get("/api/v1/family/members").json()["data"]
    assert members[0]["family_user_id"] == "demo-daughter"
    assert "assist_order" in members[0]["permissions"]
    orders = api.get("/api/v1/family/orders", params={"family_user_id": "demo-daughter"}).json()["data"]
    assert len(orders) == 4
    created = api.post("/api/v1/family/orders", json={"family_user_id": "demo-daughter", "items": [{"product_id": "rice-001", "quantity": 1}], "address_id": "address-001", "idempotency_key": "family-order-123"}).json()["data"]
    assert created["created_by_user_id"] == "demo-daughter"
    assert created["status"] == "pending_payment"


def test_elder_can_send_payment_link_and_family_can_confirm(tmp_path: Path) -> None:
    api = client(tmp_path)
    created = api.post("/api/v1/family/payment-requests", json={"elder_user_id": "demo-elder", "order_id": "order-demo-pending", "family_user_id": "demo-daughter", "note": "请帮我付款"})
    assert created.status_code == 200
    request = created.json()["data"]
    assert request["kind"] == "payment"
    assert request["share_url"] == f"/family/requests/{request['id']}"
    duplicate = api.post("/api/v1/family/payment-requests", json={"elder_user_id": "demo-elder", "order_id": "order-demo-pending", "family_user_id": "demo-daughter", "note": "重复点击"}).json()["data"]
    assert duplicate["id"] == request["id"]
    confirmed = api.post(f"/api/v1/family/requests/{request['id']}/confirm-payment", params={"family_user_id": "demo-daughter"}).json()["data"]
    assert confirmed["status"] == "completed"
    assert confirmed["order"]["status"] == "paid_pending_shipment"
    again = api.post(f"/api/v1/family/requests/{request['id']}/confirm-payment", params={"family_user_id": "demo-daughter"}).json()["data"]
    assert again["status"] == "completed"


def test_family_permissions_and_after_sale_assistance(tmp_path: Path) -> None:
    api = client(tmp_path)
    denied = api.get("/api/v1/family/orders", params={"family_user_id": "not-a-family"})
    assert denied.status_code == 403
    after_sale = api.post("/api/v1/family/after-sale-requests", json={"family_user_id": "demo-daughter", "elder_user_id": "demo-elder", "order_id": "order-demo-delivered", "note": "我来帮忙跟进"})
    assert after_sale.status_code == 200
    assert after_sale.json()["data"]["kind"] == "after_sale"
    assert after_sale.json()["data"]["status"] == "pending"


def test_family_requests_survive_restart(tmp_path: Path) -> None:
    first = client(tmp_path)
    created = first.post("/api/v1/family/payment-requests", json={"elder_user_id": "demo-elder", "order_id": "order-demo-pending", "family_user_id": "demo-daughter", "note": "持久化测试"}).json()["data"]
    second = client(tmp_path)
    requests = second.get("/api/v1/family/requests", params={"family_user_id": "demo-daughter"}).json()["data"]
    assert any(item["id"] == created["id"] for item in requests)
    assert (tmp_path / "family.sqlite3").exists()

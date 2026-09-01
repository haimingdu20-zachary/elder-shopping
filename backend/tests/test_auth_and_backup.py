import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.backup import BackupService
from app.main import create_app


def production_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("AUTH_SECRET", "test-secret-only")
    monkeypatch.setenv("INVITE_CODES", "elder:elder-code,family:family-code")
    return TestClient(create_app(tmp_path))


def token(api: TestClient, code: str) -> str:
    result = api.post("/api/v1/auth/login", json={"invite_code": code})
    assert result.status_code == 200
    return result.json()["data"]["access_token"]


def test_production_requires_signed_login_and_isolates_users(tmp_path: Path, monkeypatch) -> None:
    api = production_client(tmp_path, monkeypatch)
    assert api.get("/api/v1/orders").status_code == 401
    elder = token(api, "elder-code")
    family = token(api, "family-code")
    assert api.get("/api/v1/orders", headers={"Authorization": f"Bearer {elder}"}).json()["data"]
    assert api.get("/api/v1/orders/order-demo-pending", headers={"Authorization": f"Bearer {family}"}).status_code == 404
    assert api.get("/api/v1/family/orders", headers={"Authorization": f"Bearer {family}"}).status_code == 200
    assert api.get("/api/v1/family/orders", headers={"Authorization": f"Bearer {elder}"}).status_code == 403
    assert api.get("/api/v1/orders", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_local_backup_contains_json_and_sqlite_snapshot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BACKUP_PROVIDER", "local")
    api = TestClient(create_app(tmp_path))
    assert api.get("/api/v1/health").status_code == 200
    backup_dir = tmp_path / "snapshots"
    monkeypatch.setenv("BACKUP_DIR", str(backup_dir))
    result = BackupService(tmp_path).backup()
    snapshot = Path(result["location"])
    assert (snapshot / "products.json").exists()
    assert (snapshot / "family.sqlite3").exists()
    assert json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))["schema_version"] == 1

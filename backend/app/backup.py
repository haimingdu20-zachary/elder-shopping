from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKUP_FILES = (
    "products.json",
    "addresses.json",
    "carts.json",
    "orders.json",
    "after_sales.json",
    "assistant_audit.json",
    "family.sqlite3",
)


class BackupError(RuntimeError):
    pass


class BackupService:
    """JSON/SQLite 快照备份。

    provider=local 用于本地验收；provider=tos 使用 S3 兼容接口连接火山引擎 TOS。
    凭据只从运行环境读取，永远不写入快照或日志。
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.provider = os.getenv("BACKUP_PROVIDER", "local").strip().lower()
        self.local_dir = Path(os.getenv("BACKUP_DIR", str(self.data_dir / "backups")))
        self.prefix = os.getenv("BACKUP_PREFIX", "elder-shopping").strip("/")

    def backup(self) -> dict[str, Any]:
        if self.provider not in {"local", "tos", "s3"}:
            raise BackupError("BACKUP_PROVIDER 只支持 local 或 tos。")
        with tempfile.TemporaryDirectory(prefix="elder-shopping-backup-") as temp:
            snapshot_dir = Path(temp) / "snapshot"
            snapshot_dir.mkdir()
            manifest = self._copy_snapshot(snapshot_dir)
            if self.provider == "local":
                return self._save_local(snapshot_dir, manifest)
            return self._upload_tos(snapshot_dir, manifest)

    def restore_latest(self) -> dict[str, Any]:
        if self.provider == "local":
            snapshots = sorted(path for path in self.local_dir.iterdir() if path.is_dir()) if self.local_dir.exists() else []
            if not snapshots:
                raise BackupError("本地还没有可恢复的快照。")
            snapshot_dir = snapshots[-1]
            manifest = self._read_manifest(snapshot_dir / "manifest.json")
            self._restore_directory(snapshot_dir, manifest)
            return {"provider": "local", "location": str(snapshot_dir), "manifest": manifest}
        if self.provider not in {"tos", "s3"}:
            raise BackupError("恢复只支持 local 或 tos 备份。")
        snapshot_dir, manifest, prefix = self._download_latest_tos()
        try:
            self._restore_directory(snapshot_dir, manifest)
        finally:
            shutil.rmtree(snapshot_dir, ignore_errors=True)
        return {"provider": "tos", "prefix": prefix, "manifest": manifest}

    @staticmethod
    def _read_manifest(path: Path) -> dict[str, Any]:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), list):
                raise ValueError("unsupported manifest")
            return manifest
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise BackupError("备份清单损坏，已停止恢复。") from exc

    def _restore_directory(self, snapshot_dir: Path, manifest: dict[str, Any]) -> None:
        for name in manifest["files"]:
            if name not in BACKUP_FILES:
                raise BackupError("备份包含未允许的数据文件，已停止恢复。")
            source = snapshot_dir / name
            if not source.exists():
                raise BackupError(f"备份缺少 {name}，已停止恢复。")
            target = self.data_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(f".{target.name}.restore.tmp")
            shutil.copy2(source, temp)
            os.replace(temp, target)

    def _tos_client(self):
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise BackupError("TOS 备份需要安装 boto3 依赖。") from exc
        endpoint = os.getenv("TOS_ENDPOINT", "").strip()
        bucket = os.getenv("TOS_BUCKET", "").strip()
        access_key = os.getenv("TOS_ACCESS_KEY", "").strip()
        secret_key = os.getenv("TOS_SECRET_KEY", "").strip()
        if not endpoint or not bucket or not access_key or not secret_key:
            raise BackupError("TOS 备份缺少 TOS_ENDPOINT、TOS_BUCKET、TOS_ACCESS_KEY 或 TOS_SECRET_KEY。")
        # 火山 TOS 的 S3 兼容接口要求使用虚拟主机式寻址；默认路径式寻址会返回
        # InvalidPathAccess。桶名会被放入请求主机名中，例如 bucket.tos-s3-cn-beijing.volces.com。
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=os.getenv("TOS_REGION", "cn-beijing"),
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(s3={"addressing_style": "virtual"}),
        )
        return client, bucket

    def _download_latest_tos(self) -> tuple[Path, dict[str, Any], str]:
        client, bucket = self._tos_client()
        listing = client.list_objects_v2(Bucket=bucket, Prefix=f"{self.prefix}/")
        keys = [item["Key"] for item in listing.get("Contents", []) if item.get("Key", "").endswith("/manifest.json")]
        if not keys:
            raise BackupError("TOS 中还没有可恢复的快照。")
        manifest_key = sorted(keys)[-1]
        prefix = manifest_key.removesuffix("/manifest.json")
        temp_dir = Path(tempfile.mkdtemp(prefix="elder-shopping-restore-"))
        try:
            client.download_file(bucket, manifest_key, str(temp_dir / "manifest.json"))
            manifest = self._read_manifest(temp_dir / "manifest.json")
            for name in manifest["files"]:
                client.download_file(bucket, f"{prefix}/{name}", str(temp_dir / name))
            return temp_dir, manifest, prefix
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def _copy_snapshot(self, snapshot_dir: Path) -> dict[str, Any]:
        copied: list[str] = []
        for name in BACKUP_FILES:
            source = self.data_dir / name
            if not source.exists():
                continue
            target = snapshot_dir / name
            if name.endswith(".sqlite3"):
                self._snapshot_sqlite(source, target)
            else:
                shutil.copy2(source, target)
            copied.append(name)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        manifest = {"schema_version": 1, "created_at": timestamp, "files": copied}
        (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest

    @staticmethod
    def _snapshot_sqlite(source: Path, target: Path) -> None:
        source_db = sqlite3.connect(source)
        target_db = sqlite3.connect(target)
        try:
            source_db.backup(target_db)
        finally:
            target_db.close()
            source_db.close()

    def _save_local(self, snapshot_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        target = self.local_dir / str(manifest["created_at"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(snapshot_dir, target)
        return {"provider": "local", "location": str(target), "manifest": manifest}

    def _upload_tos(self, snapshot_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        client, bucket = self._tos_client()
        snapshot_id = str(manifest["created_at"])
        uploaded: list[str] = []
        for path in sorted(snapshot_dir.iterdir()):
            key = f"{self.prefix}/{snapshot_id}/{path.name}"
            client.upload_file(str(path), bucket, key)
            uploaded.append(key)
        return {"provider": "tos", "bucket": bucket, "prefix": f"{self.prefix}/{snapshot_id}", "files": uploaded, "manifest": manifest}

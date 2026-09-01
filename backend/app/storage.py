from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


class StorageError(RuntimeError):
    """结构化数据无法安全读取或写入。"""


class JsonStore:
    """带 schema 版本和原子写入的本地 JSON 存储。"""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        if not name.endswith(".json") or Path(name).name != name:
            raise StorageError("数据文件名不受支持。")
        return self.root / name

    def read_items(self, name: str, default: list[dict[str, Any]]) -> list[dict[str, Any]]:
        path = self._path(name)
        if not path.exists():
            self.write_items(name, default)
            return list(default)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("items"), list):
                raise StorageError(f"{name} 的数据版本不受支持。")
            return payload["items"]
        except StorageError:
            raise
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise StorageError(f"无法读取 {name}，原文件未被覆盖。") from exc

    def write_items(self, name: str, items: list[dict[str, Any]]) -> None:
        path = self._path(name)
        payload = {"schema_version": SCHEMA_VERSION, "items": items}
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.root, prefix=f".{path.stem}.", suffix=".tmp", delete=False
            ) as handle:
                temp_path = handle.name
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except OSError as exc:
            if temp_path:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except OSError:
                    pass
            raise StorageError(f"无法写入 {name}。") from exc


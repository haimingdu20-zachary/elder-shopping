from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from .service import AppError


@dataclass(frozen=True)
class Identity:
    user_id: str
    role: str
    display_name: str

    def as_dict(self) -> dict[str, str]:
        return {"user_id": self.user_id, "role": self.role, "display_name": self.display_name}


DEFAULT_USERS = {
    "elder": ("demo-elder", "王阿姨"),
    "family": ("demo-daughter", "女儿（演示）"),
}


class AuthService:
    """轻量邀请码登录。

    这是当前原型的身份适配层：令牌由后端签名，业务接口永远从令牌取 user_id，
    不信任请求体或查询参数中的 user_id。正式商业化时可替换为短信/OIDC，接口契约保持不变。
    """

    def __init__(self, environment: str):
        self.production = environment in {"prod", "production"}
        self.secret = os.getenv("AUTH_SECRET", "dev-only-auth-secret").strip()
        if self.production and (not self.secret or self.secret == "dev-only-auth-secret"):
            raise RuntimeError("生产环境必须配置 AUTH_SECRET。")
        try:
            self.ttl_seconds = max(300, int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400")))
        except ValueError:
            self.ttl_seconds = 86400
        self.invites = self._parse_invites(os.getenv("INVITE_CODES", ""))
        if not self.production and not self.invites:
            self.invites = self._parse_invites("elder:elder-demo,family:family-demo")
        if self.production and not self.invites:
            raise RuntimeError("生产环境必须配置 INVITE_CODES。")

    @staticmethod
    def _parse_invites(raw: str) -> dict[str, tuple[str, Identity]]:
        result: dict[str, tuple[str, Identity]] = {}
        for item in raw.split(","):
            fields = [field.strip() for field in item.split(":")]
            if len(fields) == 2:
                role, code = fields
                user_id, display_name = DEFAULT_USERS.get(role, (f"demo-{role}", role))
            elif len(fields) == 4:
                user_id, role, display_name, code = fields
            else:
                continue
            if role not in {"elder", "family"} or not user_id or not code:
                continue
            identity = Identity(user_id=user_id, role=role, display_name=display_name or user_id)
            result[code] = (code, identity)
        return result

    @staticmethod
    def _encode(payload: dict[str, Any]) -> str:
        encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()).decode().rstrip("=")
        return encoded

    @staticmethod
    def _decode(value: str) -> dict[str, Any]:
        padding = "=" * (-len(value) % 4)
        return json.loads(base64.urlsafe_b64decode((value + padding).encode()).decode())

    def _sign(self, payload: str) -> str:
        return base64.urlsafe_b64encode(hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).digest()).decode().rstrip("=")

    def issue(self, identity: Identity) -> str:
        payload = self._encode({"sub": identity.user_id, "role": identity.role, "name": identity.display_name, "exp": int(time.time()) + self.ttl_seconds})
        return f"{payload}.{self._sign(payload)}"

    def login(self, code: str) -> dict[str, Any]:
        submitted = code.strip()
        if not submitted:
            raise AppError("INVALID_INVITE_CODE", "请输入邀请码。", 401)
        match = next((entry for raw, entry in self.invites.items() if hmac.compare_digest(raw, submitted)), None)
        if match is None:
            raise AppError("INVALID_INVITE_CODE", "邀请码不正确，请联系家人或客服。", 401)
        identity = match[1]
        return {"access_token": self.issue(identity), "token_type": "bearer", "expires_in": self.ttl_seconds, "user": identity.as_dict()}

    def authenticate(self, request: Request) -> Identity:
        if not self.production:
            return Identity("demo-elder", "elder", "王阿姨")
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AppError("AUTH_REQUIRED", "请先登录后再继续。", 401)
        try:
            encoded_payload, signature = token.split(".", 1)
            if not hmac.compare_digest(signature, self._sign(encoded_payload)):
                raise ValueError("invalid signature")
            payload = self._decode(encoded_payload)
            if int(payload["exp"]) <= int(time.time()):
                raise ValueError("expired")
            identity = Identity(str(payload["sub"]), str(payload["role"]), str(payload.get("name") or payload["sub"]))
            if identity.role not in {"elder", "family"}:
                raise ValueError("invalid role")
            return identity
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
            raise AppError("AUTH_INVALID", "登录状态已失效，请重新登录。", 401)

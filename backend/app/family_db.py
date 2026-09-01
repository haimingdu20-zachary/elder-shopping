from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")


class FamilyLink(Base):
    __tablename__ = "family_links"
    __table_args__ = (UniqueConstraint("elder_user_id", "family_user_id", name="uq_family_link_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    elder_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    family_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    relationship: Mapped[str] = mapped_column(String(30), nullable=False)
    permissions_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)


class AssistRequest(Base):
    __tablename__ = "assist_requests"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    elder_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    family_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class FamilyDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(self.engine, expire_on_commit=False)
        self._seed()

    def _seed(self) -> None:
        from .service import now_iso

        with self.SessionLocal() as session:
            elder = session.get(User, "demo-elder")
            if elder is None:
                session.add(User(id="demo-elder", display_name="王阿姨", role="elder", status="active"))
            family = session.get(User, "demo-daughter")
            if family is None:
                session.add(User(id="demo-daughter", display_name="女儿（演示）", role="family", status="active"))
            link = session.scalar(select(FamilyLink).where(FamilyLink.elder_user_id == "demo-elder", FamilyLink.family_user_id == "demo-daughter"))
            if link is None:
                session.add(FamilyLink(
                    elder_user_id="demo-elder",
                    family_user_id="demo-daughter",
                    relationship="女儿",
                    permissions_json=json.dumps(["view_orders", "assist_order", "pay", "assist_after_sale"], ensure_ascii=False),
                    status="active",
                    created_at=now_iso(),
                ))
            session.commit()

    @staticmethod
    def permissions(link: FamilyLink) -> list[str]:
        return json.loads(link.permissions_json)

    @staticmethod
    def request_dict(record: AssistRequest) -> dict[str, Any]:
        return {
            "id": record.id,
            "elder_user_id": record.elder_user_id,
            "family_user_id": record.family_user_id,
            "kind": record.kind,
            "order_id": record.order_id,
            "status": record.status,
            "note": record.note,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "completed_at": record.completed_at,
        }

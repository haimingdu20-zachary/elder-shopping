from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CartItemRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=0, le=99)


class OrderItemRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0, le=99)


class CreateOrderRequest(BaseModel):
    items: list[OrderItemRequest] = Field(default_factory=list, max_length=30)
    address_id: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=120)


class PaymentRequest(BaseModel):
    result: Literal["success", "failed", "cancelled"]
    idempotency_key: str = Field(min_length=8, max_length=120)


class AfterSaleDraftRequest(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)
    type: Literal["refund_only", "return_and_refund"]
    reason: Literal["商品不需要了", "商品与描述不一致", "商品破损", "商品少件/漏发", "收到的商品不对", "其他原因"]
    return_method: Literal["pickup", "self_ship"] = "pickup"
    idempotency_key: str = Field(min_length=8, max_length=120)


class SubmitAfterSaleRequest(BaseModel):
    confirm: bool


class FamilyOrderRequest(BaseModel):
    family_user_id: str = Field(min_length=1, max_length=80)
    items: list[OrderItemRequest] = Field(default_factory=list, max_length=30)
    address_id: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=120)


class FamilyPaymentRequest(BaseModel):
    elder_user_id: str = Field(min_length=1, max_length=80)
    order_id: str = Field(min_length=1, max_length=80)
    family_user_id: str = Field(min_length=1, max_length=80)
    note: str = Field(default="", max_length=300)


class FamilyAfterSaleRequest(BaseModel):
    family_user_id: str = Field(min_length=1, max_length=80)
    elder_user_id: str = Field(min_length=1, max_length=80)
    order_id: str = Field(min_length=1, max_length=80)
    note: str = Field(default="", max_length=300)


class AssistantChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200)
    user_id: str = Field(default="demo-elder", min_length=1, max_length=80)
    conversation_id: str | None = Field(default=None, max_length=100)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=8)

from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

from .family_db import FamilyDatabase
from .family_service import FamilyService
from .assistant_service import AssistantService
from .knowledge_service import KnowledgeService
from .schemas import AfterSaleDraftRequest, AssistantChatRequest, CartItemRequest, CreateOrderRequest, FamilyAfterSaleRequest, FamilyOrderRequest, FamilyPaymentRequest, PaymentRequest, SubmitAfterSaleRequest
from .service import AppError, CommerceService
from .storage import JsonStore, StorageError


logger = logging.getLogger("elder-shopping")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def response(data: object, request_id: str | None = None) -> dict[str, object]:
    return {"data": data, "request_id": request_id or f"req_{uuid4().hex[:12]}"}


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    environment = os.getenv("ENV", os.getenv("APP_ENV", "development")).lower()
    default_data_dir = Path("/tmp/data") if environment in {"prod", "production"} else Path(__file__).resolve().parents[2] / "data"
    resolved_data_dir = Path(data_dir or os.getenv("DATA_DIR", default_data_dir))
    if not resolved_data_dir.is_absolute():
        resolved_data_dir = (Path(__file__).resolve().parents[2] / resolved_data_dir).resolve()
    service = CommerceService(JsonStore(resolved_data_dir), os.getenv("DEMO_USER_ID", "demo-elder"))
    configured_family_db = os.getenv("FAMILY_DB_PATH")
    family_db_path = Path(configured_family_db) if configured_family_db else resolved_data_dir / "family.sqlite3"
    if not family_db_path.is_absolute():
        family_db_path = (Path(__file__).resolve().parents[2] / family_db_path).resolve()
    family_service = FamilyService(FamilyDatabase(family_db_path), service)
    knowledge_service = KnowledgeService(JsonStore(resolved_data_dir))
    assistant_service = AssistantService(service, knowledge_service)
    app = FastAPI(title="老人购物模拟商城 API", version="0.1.0")
    app.state.service = service
    app.state.family_service = family_service
    app.state.assistant_service = assistant_service
    app.state.knowledge_service = knowledge_service
    configured_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def request_trace_middleware(request: Request, call_next):
        trace_id = request.headers.get("x-request-id") or f"trace_{uuid4().hex[:12]}"
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-request-id"] = trace_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", f"trace_{uuid4().hex[:12]}")
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}, "request_id": trace_id})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", f"trace_{uuid4().hex[:12]}")
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "请检查输入内容后再试。"}, "request_id": trace_id})

    @app.exception_handler(StorageError)
    async def storage_error_handler(request: Request, exc: StorageError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", f"trace_{uuid4().hex[:12]}")
        logger.error("storage_error trace_id=%s path=%s", trace_id, request.url.path)
        return JSONResponse(status_code=500, content={"error": {"code": "STORAGE_ERROR", "message": "演示数据暂时无法读取，请稍后再试。"}, "request_id": trace_id})

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", f"trace_{uuid4().hex[:12]}")
        logger.exception("unexpected_error trace_id=%s path=%s", trace_id, request.url.path)
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "服务暂时遇到问题，请稍后再试。"}, "request_id": trace_id})

    @app.get("/api/v1/health")
    async def health() -> dict[str, object]:
        return response({"status": "ok", "stage": "phase-6"})

    @app.get("/api/v1/categories")
    async def categories() -> dict[str, object]:
        return response(service.categories())

    @app.get("/api/v1/products")
    async def products(q: str | None = Query(default=None), category_id: str | None = Query(default=None), featured: bool | None = Query(default=None)) -> dict[str, object]:
        return response(service.list_products(q, category_id, featured))

    @app.get("/api/v1/products/{product_id}")
    async def product(product_id: str) -> dict[str, object]:
        return response(service.product(product_id))

    @app.get("/api/v1/addresses")
    async def addresses() -> dict[str, object]:
        return response(service.addresses())

    @app.get("/api/v1/cart")
    async def cart() -> dict[str, object]:
        return response(service.cart())

    @app.put("/api/v1/cart/items")
    async def update_cart(payload: CartItemRequest) -> dict[str, object]:
        return response(service.update_cart(payload.product_id, payload.quantity))

    @app.get("/api/v1/orders")
    async def orders() -> dict[str, object]:
        return response(service.orders())

    @app.get("/api/v1/orders/{order_id}")
    async def order(order_id: str) -> dict[str, object]:
        return response(service.order_detail(order_id))

    @app.post("/api/v1/orders/drafts")
    async def create_order(payload: CreateOrderRequest) -> dict[str, object]:
        return response(service.create_order_draft([item.model_dump() for item in payload.items], payload.address_id, payload.idempotency_key))

    @app.post("/api/v1/orders/{order_id}/simulate-payment")
    async def simulate_payment(order_id: str, payload: PaymentRequest) -> dict[str, object]:
        return response(service.simulate_payment(order_id, payload.result, payload.idempotency_key))

    @app.post("/api/v1/orders/{order_id}/confirm-receipt")
    async def confirm_receipt(order_id: str) -> dict[str, object]:
        return response(service.confirm_receipt(order_id))

    @app.post("/api/v1/after-sales/drafts")
    async def create_after_sale(payload: AfterSaleDraftRequest) -> dict[str, object]:
        return response(service.create_after_sale_draft(payload.order_id, payload.type, payload.reason, payload.return_method, payload.idempotency_key))

    @app.post("/api/v1/after-sales/{after_sale_id}/submit")
    async def submit_after_sale(after_sale_id: str, payload: SubmitAfterSaleRequest) -> dict[str, object]:
        return response(service.submit_after_sale(after_sale_id, payload.confirm))

    @app.get("/api/v1/after-sales/{after_sale_id}")
    async def get_after_sale(after_sale_id: str) -> dict[str, object]:
        return response(service.after_sale(after_sale_id))

    @app.get("/api/v1/family/members")
    async def family_members(elder_user_id: str = Query(default="demo-elder")) -> dict[str, object]:
        return response(family_service.members(elder_user_id))

    @app.post("/api/v1/assistant/chat")
    async def assistant_chat(payload: AssistantChatRequest) -> dict[str, object]:
        return response(await assistant_service.chat(payload.text, payload.user_id, payload.history, payload.conversation_id))

    @app.get("/api/v1/knowledge/search")
    async def knowledge_search(q: str = Query(..., min_length=1, max_length=200)) -> dict[str, object]:
        return response(knowledge_service.search(q))

    @app.get("/api/v1/family/orders")
    async def family_orders(family_user_id: str = Query(...)) -> dict[str, object]:
        return response(family_service.orders(family_user_id))

    @app.get("/api/v1/family/orders/{order_id}")
    async def family_order(order_id: str, family_user_id: str = Query(...)) -> dict[str, object]:
        return response(family_service.order_detail(order_id, family_user_id))

    @app.post("/api/v1/family/orders")
    async def create_family_order(payload: FamilyOrderRequest) -> dict[str, object]:
        return response(family_service.create_order(payload.family_user_id, [item.model_dump() for item in payload.items], payload.address_id, payload.idempotency_key))

    @app.post("/api/v1/family/payment-requests")
    async def create_family_payment_request(payload: FamilyPaymentRequest) -> dict[str, object]:
        return response(family_service.create_payment_request(payload.elder_user_id, payload.order_id, payload.family_user_id, payload.note))

    @app.get("/api/v1/family/requests")
    async def family_requests(family_user_id: str = Query(...)) -> dict[str, object]:
        return response(family_service.requests(family_user_id))

    @app.get("/api/v1/family/requests/{request_id}")
    async def family_request(request_id: str, family_user_id: str = Query(...)) -> dict[str, object]:
        return response(family_service.request_detail(request_id, family_user_id))

    @app.post("/api/v1/family/requests/{request_id}/confirm-payment")
    async def confirm_family_payment(request_id: str, family_user_id: str = Query(...)) -> dict[str, object]:
        return response(family_service.confirm_payment(request_id, family_user_id))

    @app.post("/api/v1/family/requests/{request_id}/cancel")
    async def cancel_family_request(request_id: str, family_user_id: str = Query(...)) -> dict[str, object]:
        return response(family_service.cancel_request(request_id, family_user_id))

    @app.post("/api/v1/family/after-sale-requests")
    async def create_family_after_sale_request(payload: FamilyAfterSaleRequest) -> dict[str, object]:
        return response(family_service.create_after_sale_request(payload.family_user_id, payload.elder_user_id, payload.order_id, payload.note))

    return app


app = create_app()

import { getSession, type UserSession } from "@/lib/auth";

const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
export const API_BASE = configuredApiBase || (process.env.NODE_ENV === "production" ? "/api/v1" : "http://127.0.0.1:8001/api/v1");

export type Product = {
  id: string; name: string; image_url: string; price: number; unit_label: string;
  category_id: string; category_name: string; stock: number; stock_text: string;
  estimated_delivery_text: string; is_featured: boolean; specification?: string;
  delivery_area?: string; return_policy?: string;
};
export type Cart = { items: { product: Product; quantity: number; item_total: number }[]; items_amount: number; shipping_fee: number; total_amount: number };
export type Address = { id: string; name: string; phone: string; full_address: string; is_default: boolean };
export type OrderItem = { product_id: string; name: string; image_url: string; price: number; unit_label: string; quantity: number; item_total: number };
export type Order = { id: string; items: OrderItem[]; total_amount: number; status: string; status_label: string; next_action: string; created_at: string; updated_at: string };
export type OrderDetail = Order & { items_amount: number; shipping_fee: number; address_snapshot: Address; payment_status: string; delivery_status: string; after_sale_status: string; logistics_text: string; can_apply_after_sale: boolean; can_confirm_receipt: boolean; can_pay: boolean };
export type AfterSale = { id: string; order_id: string; type: string; reason: string; refund_amount: number; refund_destination: string; return_method: string; status: string; status_label: string };
export type FamilyMember = { family_user_id: string; relationship: string; permissions: string[]; status: string };
export type FamilyOrder = Order & { elder_user_id: string; created_by_user_id: string };
export type FamilyRequest = { id: string; elder_user_id: string; family_user_id: string; kind: string; kind_label: string; order_id: string | null; status: string; status_label: string; note: string; created_at: string; updated_at: string; completed_at: string | null; share_url?: string; order?: OrderDetail };
export type AssistantResult = { intent: string; reply: string; action: { type: string; query?: string; product_ids?: string[]; filter?: string; sources?: { source_id: string; title: string }[] } | null; needs_confirmation: boolean; suggestions: string[]; provider?: string; model?: string; warning?: string; latency_ms?: number; usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number }; tool_calls?: string[] };
export type AssistantHistoryMessage = { role: "user" | "assistant"; content: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getSession()?.access_token;
  const result = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(init?.headers ?? {}) }, cache: "no-store" });
  const payload = await result.json();
  if (!result.ok) throw new Error(payload?.error?.message ?? "服务暂时遇到问题，请稍后再试。");
  return payload.data as T;
}

export const api = {
  login: (invite_code: string) => request<UserSession>("/auth/login", { method: "POST", body: JSON.stringify({ invite_code }) }),
  me: () => request<UserSession["user"]>("/auth/me"),
  categories: () => request<{ id: string; name: string }[]>("/categories"),
  products: (params = "") => request<Product[]>(`/products${params ? `?${params}` : ""}`),
  product: (id: string) => request<Product>(`/products/${id}`),
  addresses: () => request<Address[]>("/addresses"),
  cart: () => request<Cart>("/cart"),
  updateCart: (product_id: string, quantity: number) => request<Cart>("/cart/items", { method: "PUT", body: JSON.stringify({ product_id, quantity }) }),
  orders: () => request<Order[]>("/orders"),
  order: (id: string) => request<OrderDetail>(`/orders/${id}`),
  createOrder: (items: { product_id: string; quantity: number }[], address_id: string) => request<OrderDetail>("/orders/drafts", { method: "POST", body: JSON.stringify({ items, address_id, idempotency_key: `web-order-${crypto.randomUUID()}` }) }),
  pay: (id: string, result: "success" | "failed" | "cancelled") => request<{ order: OrderDetail; message: string }>(`/orders/${id}/simulate-payment`, { method: "POST", body: JSON.stringify({ result, idempotency_key: `web-pay-${crypto.randomUUID()}` }) }),
  confirmReceipt: (id: string) => request<OrderDetail>(`/orders/${id}/confirm-receipt`, { method: "POST" }),
  createAfterSale: (payload: { order_id: string; type: "refund_only" | "return_and_refund"; reason: string; return_method: "pickup" | "self_ship" }) => request<AfterSale>("/after-sales/drafts", { method: "POST", body: JSON.stringify({ ...payload, idempotency_key: `web-after-sale-${crypto.randomUUID()}` }) }),
  submitAfterSale: (id: string) => request<AfterSale>(`/after-sales/${id}/submit`, { method: "POST", body: JSON.stringify({ confirm: true }) }),
  familyMembers: () => request<FamilyMember[]>("/family/members"),
  familyOrders: (family_user_id = "demo-daughter") => request<FamilyOrder[]>(`/family/orders?family_user_id=${encodeURIComponent(family_user_id)}`),
  familyOrder: (id: string, family_user_id = "demo-daughter") => request<OrderDetail>(`/family/orders/${id}?family_user_id=${encodeURIComponent(family_user_id)}`),
  familyCreateOrder: (payload: { family_user_id: string; items: { product_id: string; quantity: number }[]; address_id: string }) => request<OrderDetail>("/family/orders", { method: "POST", body: JSON.stringify({ ...payload, idempotency_key: `family-order-${crypto.randomUUID()}` }) }),
  createFamilyPaymentRequest: (order_id: string, note = "") => request<FamilyRequest>("/family/payment-requests", { method: "POST", body: JSON.stringify({ elder_user_id: "demo-elder", order_id, family_user_id: "demo-daughter", note }) }),
  familyRequests: (family_user_id = "demo-daughter") => request<FamilyRequest[]>(`/family/requests?family_user_id=${encodeURIComponent(family_user_id)}`),
  familyRequest: (id: string, family_user_id = "demo-daughter") => request<FamilyRequest>(`/family/requests/${id}?family_user_id=${encodeURIComponent(family_user_id)}`),
  confirmFamilyPayment: (id: string, family_user_id = "demo-daughter") => request<FamilyRequest>(`/family/requests/${id}/confirm-payment?family_user_id=${encodeURIComponent(family_user_id)}`, { method: "POST" }),
  cancelFamilyRequest: (id: string, family_user_id = "demo-daughter") => request<FamilyRequest>(`/family/requests/${id}/cancel?family_user_id=${encodeURIComponent(family_user_id)}`, { method: "POST" }),
  createAfterSaleAssistance: (order_id: string, note = "") => request<FamilyRequest>("/family/after-sale-requests", { method: "POST", body: JSON.stringify({ family_user_id: "demo-daughter", elder_user_id: "demo-elder", order_id, note }) }),
  assistantChat: (text: string, user_id = "demo-elder", history: AssistantHistoryMessage[] = [], conversation_id?: string) => request<AssistantResult>("/assistant/chat", { method: "POST", body: JSON.stringify({ text, user_id, history, conversation_id }) }),
};

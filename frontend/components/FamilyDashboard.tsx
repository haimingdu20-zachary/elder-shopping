"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import LargeButton from "@/components/LargeButton";
import OrderStatus from "@/components/OrderStatus";
import { api, type Address, type FamilyMember, type FamilyOrder, type FamilyRequest, type Product } from "@/lib/api";

const permissionLabels: Record<string, string> = { view_orders: "查看订单", assist_order: "帮忙下单", pay: "代为付款", assist_after_sale: "协助售后" };

export default function FamilyDashboard() {
  const [member, setMember] = useState<FamilyMember | null>(null);
  const [orders, setOrders] = useState<FamilyOrder[]>([]);
  const [requests, setRequests] = useState<FamilyRequest[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [addressId, setAddressId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [members, nextOrders, nextRequests, nextProducts, nextAddresses] = await Promise.all([api.familyMembers(), api.familyOrders(), api.familyRequests(), api.products("featured=true"), api.addresses()]);
      setMember(members[0] ?? null); setOrders(nextOrders); setRequests(nextRequests); setProducts(nextProducts); setAddresses(nextAddresses);
      setProductId(nextProducts[0]?.id ?? ""); setAddressId(nextAddresses.find((item) => item.is_default)?.id ?? nextAddresses[0]?.id ?? "");
    } catch (err) { setError(err instanceof Error ? err.message : "家人协助信息暂时无法加载。"); }
  }
  useEffect(() => { load(); }, []);

  async function createOrder() {
    if (!productId || !addressId) return;
    setBusy(true); setError(""); setMessage("");
    try { const order = await api.familyCreateOrder({ family_user_id: "demo-daughter", items: [{ product_id: productId, quantity }], address_id: addressId }); setMessage(`已为王阿姨生成订单 ${order.id}，接下来可由家人代付。`); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "家人代买暂时无法完成。"); }
    finally { setBusy(false); }
  }

  async function assistAfterSale(orderId: string) {
    setBusy(true); setError(""); setMessage("");
    try { const request = await api.createAfterSaleAssistance(orderId, "请帮忙查看这笔订单的售后处理。"); setMessage(`已创建协助售后请求：${request.id}`); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "协助售后暂时无法创建。"); }
    finally { setBusy(false); }
  }

  return <div className="space-y-5">
    <div><p className="text-base font-bold text-emerald-700">家人账号：女儿（演示）</p><h1 className="mt-1 text-3xl font-black">家人协助</h1><p className="mt-2 text-slate-600">帮助王阿姨买东西、付款和处理售后。</p></div>
    {error && <p role="alert" className="rounded-2xl bg-red-50 p-3 font-bold text-red-800">{error}</p>}
    {message && <p className="rounded-2xl bg-emerald-100 p-3 font-bold text-emerald-900">{message}</p>}
    {member && <section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">已绑定家人</h2><p><strong>王阿姨</strong> · {member.relationship}</p><div className="flex flex-wrap gap-2">{member.permissions.map((permission) => <span key={permission} className="rounded-full bg-emerald-100 px-3 py-1 text-base font-bold text-emerald-900">{permissionLabels[permission] ?? permission}</span>)}</div></section>}
    <section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">家人代买</h2><p className="text-slate-600">选好商品后，订单会寄到王阿姨的默认地址。</p><label className="block font-bold">商品<select value={productId} onChange={(event) => setProductId(event.target.value)} className="focus-ring mt-1 min-h-12 w-full rounded-2xl border-2 border-slate-200 bg-white px-3">{products.map((product) => <option key={product.id} value={product.id}>{product.name} · ¥{product.price}/{product.unit_label}</option>)}</select></label><label className="block font-bold">数量<input type="number" min={1} max={9} value={quantity} onChange={(event) => setQuantity(Math.max(1, Number(event.target.value) || 1))} className="focus-ring mt-1 min-h-12 w-full rounded-2xl border-2 border-slate-200 px-3" /></label><label className="block font-bold">收货地址<select value={addressId} onChange={(event) => setAddressId(event.target.value)} className="focus-ring mt-1 min-h-12 w-full rounded-2xl border-2 border-slate-200 bg-white px-3">{addresses.map((address) => <option key={address.id} value={address.id}>{address.full_address}</option>)}</select></label><LargeButton disabled={busy || !productId || !addressId} onClick={createOrder} className="w-full bg-emerald-700 text-white">{busy ? "正在生成……" : "生成家人代买订单"}</LargeButton></section>
    <section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">待处理请求</h2>{requests.length === 0 && <p className="text-slate-600">暂时没有家人协助请求。</p>}{requests.map((request) => <div key={request.id} className="rounded-2xl border-2 border-slate-100 p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-black">{request.kind_label}</p><p className="text-base text-slate-600">{request.order?.items.map((item) => item.name).join("、")}</p></div><span className="rounded-full bg-amber-100 px-3 py-1 text-base font-black text-amber-900">{request.status_label}</span></div>{request.note && <p className="mt-2 text-base text-slate-600">备注：{request.note}</p>}{request.kind === "payment" && request.status === "pending" && <Link href={`/family/requests/${request.id}`} className="focus-ring mt-3 inline-flex rounded-2xl bg-emerald-700 px-4 py-3 font-black text-white">查看并确认代付</Link>}</div>)}</section>
    <section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">王阿姨的订单</h2>{orders.map((order) => <div key={order.id} className="rounded-2xl border-2 border-slate-100 p-4"><div className="flex items-start justify-between gap-3"><div><Link href={`/family/orders/${order.id}?family_user_id=demo-daughter`} className="focus-ring font-black text-emerald-800">{order.items.map((item) => item.name).join("、")}</Link><p className="text-base text-slate-600">¥{order.total_amount} · {order.created_by_user_id === "demo-daughter" ? "家人代买" : "王阿姨下单"}</p></div><OrderStatus status={order.status} label={order.status_label} /></div>{order.status === "delivered" && <LargeButton disabled={busy} onClick={() => assistAfterSale(order.id)} className="mt-3 w-full bg-violet-700 text-white">请家人协助售后</LargeButton>}</div>)}</section>
  </div>;
}

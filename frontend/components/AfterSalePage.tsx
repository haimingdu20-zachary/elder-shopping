"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import LargeButton from "@/components/LargeButton";
import { api, type AfterSale, type OrderDetail } from "@/lib/api";

const reasons = ["商品不需要了", "商品与描述不一致", "商品破损", "商品少件/漏发", "收到的商品不对", "其他原因"];

export default function AfterSalePage({ orderId }: { orderId: string }) {
  const router = useRouter();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [sale, setSale] = useState<AfterSale | null>(null);
  const [type, setType] = useState<"refund_only" | "return_and_refund">("return_and_refund");
  const [reason, setReason] = useState(reasons[0]);
  const [returnMethod, setReturnMethod] = useState<"pickup" | "self_ship">("pickup");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { api.order(orderId).then(setOrder).catch((err) => setError(err instanceof Error ? err.message : "订单暂时无法打开。")); }, [orderId]);
  async function createDraft() { setBusy(true); setError(""); try { setSale(await api.createAfterSale({ order_id: orderId, type, reason, return_method: returnMethod })); } catch (err) { setError(err instanceof Error ? err.message : "售后申请暂时无法创建。"); } finally { setBusy(false); } }
  async function submit() { if (!sale) return; setBusy(true); setError(""); try { await api.submitAfterSale(sale.id); router.push(`/orders/${orderId}`); } catch (err) { setError(err instanceof Error ? err.message : "售后暂时无法提交。"); } finally { setBusy(false); } }
  if (!order) return <p className="rounded-2xl bg-white p-6 text-center font-bold">正在准备售后申请……</p>;
  return <div className="space-y-5"><Link href={`/orders/${orderId}`} className="focus-ring inline-flex rounded-xl px-2 py-1 font-black text-emerald-800">← 返回订单</Link><h1 className="text-3xl font-black">申请退款/退货</h1><section className="rounded-3xl bg-white p-5 shadow-soft"><p className="font-black">{order.items.map((item) => `${item.name} × ${item.quantity}`).join("、")}</p><p className="mt-2 text-lg">最多可退：<strong className="text-emerald-700">¥{order.total_amount}</strong></p></section>{error && <p role="alert" className="rounded-2xl bg-red-50 p-3 font-bold text-red-800">{error}</p>}{!sale ? <><section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">您想怎么处理？</h2><label className="flex gap-3 rounded-2xl border-2 border-slate-100 p-3"><input type="radio" checked={type === "refund_only"} onChange={() => setType("refund_only")} name="type" className="mt-1 h-5 w-5 accent-emerald-700" /><span><b>仅退款</b><br /><small>商品还没有寄出时使用</small></span></label><label className="flex gap-3 rounded-2xl border-2 border-slate-100 p-3"><input type="radio" checked={type === "return_and_refund"} onChange={() => setType("return_and_refund")} name="type" className="mt-1 h-5 w-5 accent-emerald-700" /><span><b>退货退款</b><br /><small>商品寄回后退款（模拟）</small></span></label><h2 className="pt-2 text-xl font-black">请选择原因</h2><select value={reason} onChange={(event) => setReason(event.target.value)} className="focus-ring min-h-12 w-full rounded-2xl border-2 border-slate-200 bg-white px-3">{reasons.map((item) => <option key={item}>{item}</option>)}</select>{type === "return_and_refund" && <><h2 className="pt-2 text-xl font-black">退货方式</h2><select value={returnMethod} onChange={(event) => setReturnMethod(event.target.value as "pickup" | "self_ship")} className="focus-ring min-h-12 w-full rounded-2xl border-2 border-slate-200 bg-white px-3"><option value="pickup">上门取件（模拟）</option><option value="self_ship">自行寄回（模拟）</option></select></>}</section><LargeButton disabled={busy} onClick={createDraft} className="w-full bg-emerald-700 text-white">查看退款确认</LargeButton></> : <section className="space-y-4 rounded-3xl bg-amber-50 p-5"><h2 className="text-2xl font-black">请确认售后信息</h2><p>处理方式：{sale.type === "refund_only" ? "仅退款" : "退货退款"}</p><p>原因：{sale.reason}</p><p>退款金额：<strong className="text-emerald-700">¥{sale.refund_amount}</strong></p><p>退款去向：{sale.refund_destination}</p><p>退货方式：{sale.return_method === "pickup" ? "上门取件（模拟）" : "自行寄回（模拟）"}</p><div className="grid grid-cols-2 gap-3"><LargeButton onClick={() => setSale(null)} className="bg-white">返回修改</LargeButton><LargeButton disabled={busy} onClick={submit} className="bg-emerald-700 text-white">确认提交</LargeButton></div></section>}</div>;
}


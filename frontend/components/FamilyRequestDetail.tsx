"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import LargeButton from "@/components/LargeButton";
import { api, type FamilyRequest } from "@/lib/api";

export default function FamilyRequestDetail({ id }: { id: string }) {
  const [request, setRequest] = useState<FamilyRequest | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.familyRequest(id).then(setRequest).catch((err) => setError(err instanceof Error ? err.message : "协助请求暂时无法打开。")); }, [id]);
  async function confirm() { setBusy(true); setError(""); try { setRequest(await api.confirmFamilyPayment(id)); setMessage("模拟付款成功，王阿姨的订单已进入待发货。"); } catch (err) { setError(err instanceof Error ? err.message : "模拟付款暂时无法完成。"); } finally { setBusy(false); } }
  async function cancel() { setBusy(true); setError(""); try { setRequest(await api.cancelFamilyRequest(id)); setMessage("已取消这条代付请求。"); } catch (err) { setError(err instanceof Error ? err.message : "暂时无法取消请求。"); } finally { setBusy(false); } }
  if (error && !request) return <p role="alert" className="rounded-2xl bg-red-50 p-5 font-bold text-red-800">{error}</p>;
  if (!request) return <p className="rounded-2xl bg-white p-6 text-center font-bold">正在打开协助请求……</p>;
  const order = request.order;
  return <div className="space-y-5"><Link href="/family" className="focus-ring inline-flex rounded-xl px-2 py-1 font-black text-emerald-800">← 返回家人协助</Link><div><p className="text-base text-slate-500">请求号：{request.id}</p><h1 className="mt-1 text-3xl font-black">{request.kind_label}</h1></div>{message && <p className="rounded-2xl bg-emerald-100 p-3 font-bold text-emerald-900">{message}</p>}{error && <p role="alert" className="rounded-2xl bg-red-50 p-3 font-bold text-red-800">{error}</p>}<section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><p className="font-black">订单商品</p>{order?.items.map((item) => <p key={item.product_id}>{item.name} × {item.quantity} <span className="float-right font-bold">¥{item.item_total}</span></p>)}<p className="flex justify-between border-t border-slate-100 pt-3 text-2xl font-black"><span>应付金额</span><strong className="text-emerald-700">¥{order?.total_amount}</strong></p><p>收货地址：{order?.address_snapshot.full_address}</p><p className="rounded-2xl bg-blue-50 p-3 font-bold text-blue-900">{order?.logistics_text}</p></section>{request.status === "pending" && request.kind === "payment" ? <section className="space-y-3 rounded-3xl bg-amber-50 p-5"><p>这是模拟付款，不会产生真实扣款。</p><div className="grid grid-cols-2 gap-3"><LargeButton disabled={busy} onClick={cancel} className="bg-white">取消请求</LargeButton><LargeButton disabled={busy} onClick={confirm} className="bg-emerald-700 text-white">确认模拟付款</LargeButton></div></section> : <section className="rounded-3xl bg-white p-5 shadow-soft"><p className="text-lg font-black">当前状态：{request.status_label}</p><p className="mt-2 text-slate-600">这条请求已经处理完毕，可以返回家人协助查看其他订单。</p></section>}</div>;
}

"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import OrderStatus from "@/components/OrderStatus";
import { api, type OrderDetail } from "@/lib/api";

export default function FamilyOrderDetail({ id }: { id: string }) {
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api.familyOrder(id).then(setOrder).catch((err) => setError(err instanceof Error ? err.message : "共享订单暂时无法打开。")); }, [id]);
  if (error) return <p role="alert" className="rounded-2xl bg-red-50 p-5 font-bold text-red-800">{error}</p>;
  if (!order) return <p className="rounded-2xl bg-white p-6 text-center font-bold">正在打开共享订单……</p>;
  return <div className="space-y-5"><Link href="/family" className="focus-ring inline-flex rounded-xl px-2 py-1 font-black text-emerald-800">← 返回家人协助</Link><div className="flex items-start justify-between gap-3"><div><p className="text-base text-slate-500">订单号：{order.id}</p><h1 className="mt-1 text-3xl font-black">共享订单详情</h1></div><OrderStatus status={order.status} label={order.status_label} /></div><section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">商品</h2>{order.items.map((item) => <div key={item.product_id} className="flex items-center gap-3 border-b border-slate-100 pb-3"><Image src={item.image_url} alt="" width={56} height={56} className="h-14 w-14 rounded-xl bg-emerald-50 object-cover" /><p className="flex-1 font-black">{item.name} × {item.quantity}</p><b>¥{item.item_total}</b></div>)}<p className="flex justify-between border-t border-slate-100 pt-3 text-2xl font-black"><span>订单金额</span><strong className="text-emerald-700">¥{order.total_amount}</strong></p></section><section className="space-y-2 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">配送信息</h2><p>{order.address_snapshot.name} {order.address_snapshot.phone}</p><p>{order.address_snapshot.full_address}</p><p className="rounded-2xl bg-blue-50 p-3 font-bold text-blue-900">{order.logistics_text}</p></section><p className="rounded-2xl bg-emerald-100 p-4 font-bold text-emerald-900">这是家人共享信息页面，家人不能修改王阿姨的地址或订单。</p></div>;
}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import OrderStatus from "@/components/OrderStatus";
import SupportEntry from "@/components/SupportEntry";
import { api, type Order } from "@/lib/api";

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api.orders().then(setOrders).catch((err) => setError(err instanceof Error ? err.message : "订单暂时无法加载。")); }, []);
  return <div className="space-y-5"><Link href="/" className="focus-ring inline-flex rounded-xl px-2 py-1 font-black text-emerald-800">← 回到首页</Link><div className="flex items-center justify-between"><h1 className="text-3xl font-black">我的订单</h1><Link href="/cart" className="focus-ring rounded-xl bg-white px-4 py-2 font-black text-emerald-800">购物车</Link></div>{error && <p role="alert" className="rounded-2xl bg-red-50 p-3 font-bold text-red-800">{error}</p>}{orders.length ? <div className="space-y-3">{orders.map((order) => <Link key={order.id} href={`/orders/${order.id}`} className="focus-ring block rounded-3xl bg-white p-4 shadow-soft transition hover:-translate-y-0.5"><div className="flex items-start justify-between gap-3"><div><p className="text-base text-slate-500">订单号：{order.id}</p><h2 className="mt-1 text-xl font-black">{order.items.map((item) => `${item.name} × ${item.quantity}`).join("、")}</h2></div><OrderStatus status={order.status} label={order.status_label} /></div><div className="mt-4 flex items-end justify-between"><span className="text-base text-slate-600">{order.next_action}</span><strong className="text-xl text-emerald-700">¥{order.total_amount}</strong></div></Link>)}</div> : <p className="rounded-3xl bg-white p-8 text-center font-bold">还没有订单。</p>}<SupportEntry /></div>;
}


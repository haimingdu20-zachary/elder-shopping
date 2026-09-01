"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import SupportEntry from "@/components/SupportEntry";
import { api, type Cart } from "@/lib/api";

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState("");
  async function load() { try { setCart(await api.cart()); } catch (err) { setError(err instanceof Error ? err.message : "购物车暂时无法打开。"); } }
  useEffect(() => { load(); }, []);
  async function update(id: string, quantity: number) { try { setCart(await api.updateCart(id, quantity)); } catch (err) { setError(err instanceof Error ? err.message : "数量暂时无法修改。"); } }
  if (!cart) return <p className="rounded-2xl bg-white p-6 text-center font-bold">正在打开购物车……</p>;
  return <div className="space-y-5"><Link href="/" className="focus-ring inline-flex rounded-xl px-2 py-1 font-black text-emerald-800">← 继续买东西</Link><h1 className="text-3xl font-black">购物车</h1>{error && <p role="alert" className="rounded-2xl bg-red-50 p-3 font-bold text-red-800">{error}</p>}{cart.items.length === 0 ? <div className="space-y-4 rounded-3xl bg-white p-8 text-center"><p className="text-xl font-bold">购物车还是空的</p><Link href="/" className="focus-ring inline-flex rounded-2xl bg-emerald-700 px-5 py-3 font-black text-white">去看看商品</Link></div> : <><div className="space-y-3">{cart.items.map((item) => <div key={item.product.id} className="flex items-center gap-3 rounded-3xl bg-white p-3 shadow-soft"><Image src={item.product.image_url} alt="" width={80} height={80} className="h-20 w-20 rounded-2xl bg-emerald-50 object-cover" /><div className="min-w-0 flex-1"><h2 className="truncate text-xl font-black">{item.product.name}</h2><p className="text-base text-slate-600">¥{item.product.price} / {item.product.unit_label}</p><div className="mt-2 flex items-center gap-2"><button aria-label="减少数量" onClick={() => update(item.product.id, item.quantity - 1)} className="focus-ring h-10 w-10 rounded-full bg-slate-100 text-xl font-black">−</button><span className="w-8 text-center font-black">{item.quantity}</span><button aria-label="增加数量" onClick={() => update(item.product.id, item.quantity + 1)} className="focus-ring h-10 w-10 rounded-full bg-emerald-100 text-xl font-black">＋</button></div></div><strong className="text-xl text-emerald-700">¥{item.item_total}</strong></div>)}</div><div className="space-y-2 rounded-3xl bg-white p-5 shadow-soft"><p className="flex justify-between"><span>商品金额</span><b>¥{cart.items_amount}</b></p><p className="flex justify-between"><span>运费</span><b>¥{cart.shipping_fee}</b></p><p className="flex justify-between border-t border-slate-100 pt-3 text-2xl font-black"><span>合计</span><strong className="text-emerald-700">¥{cart.total_amount}</strong></p><Link href="/checkout" className="focus-ring mt-3 block rounded-2xl bg-emerald-700 px-5 py-4 text-center text-xl font-black text-white">去确认订单</Link></div></>}<SupportEntry /></div>;
}

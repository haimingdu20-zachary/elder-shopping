"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import LargeButton from "@/components/LargeButton";
import { api, type Address, type Cart } from "@/lib/api";

export default function CheckoutPage() {
  const router = useRouter();
  const [cart, setCart] = useState<Cart | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressId, setAddressId] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { Promise.all([api.cart(), api.addresses()]).then(([nextCart, nextAddresses]) => { setCart(nextCart); setAddresses(nextAddresses); setAddressId(nextAddresses.find((item) => item.is_default)?.id ?? nextAddresses[0]?.id ?? ""); }).catch((err) => setError(err instanceof Error ? err.message : "订单信息暂时无法加载。")); }, []);
  const address = addresses.find((item) => item.id === addressId);
  async function createOrder() { if (!cart || !addressId) return; setBusy(true); setError(""); try { const order = await api.createOrder(cart.items.map((item) => ({ product_id: item.product.id, quantity: item.quantity })), addressId); router.push(`/orders/${order.id}?new=1`); } catch (err) { setError(err instanceof Error ? err.message : "订单暂时无法创建。"); setBusy(false); } }
  if (!cart) return <p className="rounded-2xl bg-white p-6 text-center font-bold">正在准备确认订单……</p>;
  if (cart.items.length === 0) return <div className="space-y-4 rounded-3xl bg-white p-8 text-center"><h1 className="text-2xl font-black">购物车还是空的</h1><Link href="/" className="focus-ring inline-flex rounded-2xl bg-emerald-700 px-5 py-3 font-black text-white">去选商品</Link></div>;
  return <div className="space-y-5"><Link href="/cart" className="focus-ring inline-flex rounded-xl px-2 py-1 font-black text-emerald-800">← 返回购物车</Link><h1 className="text-3xl font-black">确认订单</h1><section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">您要购买</h2>{cart.items.map((item) => <div key={item.product.id} className="flex justify-between gap-3 border-b border-slate-100 py-2"><span>{item.product.name} × {item.quantity}</span><b>¥{item.item_total}</b></div>)}<p className="flex justify-between pt-2 text-2xl font-black"><span>共计</span><strong className="text-emerald-700">¥{cart.total_amount}</strong></p></section><section className="space-y-3 rounded-3xl bg-white p-5 shadow-soft"><h2 className="text-xl font-black">收货地址</h2>{addresses.map((item) => <label key={item.id} className={`flex cursor-pointer gap-3 rounded-2xl border-2 p-3 ${item.id === addressId ? "border-emerald-600 bg-emerald-50" : "border-slate-100"}`}><input type="radio" name="address" checked={item.id === addressId} onChange={() => setAddressId(item.id)} className="mt-1 h-5 w-5 accent-emerald-700" /><span><b>{item.name} {item.phone}</b><br />{item.full_address}</span></label>)}</section><section className="rounded-3xl bg-amber-50 p-5 text-lg"><p className="font-black">配送信息</p><p className="mt-1">预计明天或后天送达（模拟信息）</p></section>{error && <p role="alert" className="rounded-2xl bg-red-50 p-3 font-bold text-red-800">{error}</p>}<LargeButton disabled={busy || !address} onClick={() => setConfirming(true)} className="w-full bg-emerald-700 text-white">确认商品和金额</LargeButton>{confirming && address && <div className="fixed inset-0 z-10 flex items-end justify-center bg-ink/50 p-3 sm:items-center"><div role="dialog" aria-modal="true" className="w-full max-w-lg space-y-4 rounded-3xl bg-white p-6 shadow-soft"><h2 className="text-2xl font-black">请您再确认一次</h2><p>您要购买 {cart.items.map((item) => `${item.product.name}${item.quantity}件`).join("、")}，共 <b className="text-emerald-700">¥{cart.total_amount}</b>。</p><p>送到：{address.full_address}<br />预计明天或后天送达。</p><div className="grid grid-cols-2 gap-3"><LargeButton onClick={() => setConfirming(false)} className="bg-slate-100">我再看看</LargeButton><LargeButton disabled={busy} onClick={createOrder} className="bg-emerald-700 text-white">{busy ? "正在创建……" : "确认并生成订单"}</LargeButton></div></div></div>}</div>;
}


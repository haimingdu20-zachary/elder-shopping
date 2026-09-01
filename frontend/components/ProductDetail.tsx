"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import LargeButton from "@/components/LargeButton";
import SupportEntry from "@/components/SupportEntry";
import { api, type Product } from "@/lib/api";

export default function ProductDetail({ id }: { id: string }) {
  const router = useRouter();
  const [product, setProduct] = useState<Product | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { api.product(id).then(setProduct).catch((err) => setError(err instanceof Error ? err.message : "商品暂时无法加载。")); }, [id]);

  async function addAndGo() {
    if (!product) return;
    setMessage(""); setError("");
    try { await api.updateCart(product.id, quantity); setMessage("已经放进购物车了。"); router.push("/cart"); }
    catch (err) { setError(err instanceof Error ? err.message : "暂时无法加入购物车。"); }
  }

  if (error) return <p role="alert" className="rounded-2xl bg-red-50 p-5 font-bold text-red-800">{error}</p>;
  if (!product) return <p className="rounded-2xl bg-white p-6 text-center font-bold">正在打开商品……</p>;
  return <div className="space-y-5">
    <Link href="/" className="focus-ring inline-flex rounded-xl px-2 py-1 font-black text-emerald-800">← 返回商品</Link>
    <article className="overflow-hidden rounded-3xl bg-white shadow-soft">
      <div className="relative flex h-64 items-center justify-center bg-emerald-50"><Image src={product.image_url} alt="" className="object-cover" fill sizes="(max-width: 640px) 100vw, 768px" /></div>
      <div className="space-y-5 p-5">
        <div><p className="text-base font-bold text-emerald-700">{product.category_name}</p><h1 className="mt-1 text-3xl font-black">{product.name}</h1><p className="mt-2 text-lg text-slate-700">{product.specification}</p></div>
        <div className="flex items-end gap-2"><strong className="text-4xl font-black text-emerald-700">¥{product.price}</strong><span className="pb-1 text-lg">/{product.unit_label}</span></div>
        <div className="space-y-2 rounded-2xl bg-emerald-50 p-4 text-lg"><p><b>配送范围：</b>{product.delivery_area}</p><p><b>送达时间：</b>{product.estimated_delivery_text}</p><p><b>退货规则：</b>{product.return_policy}</p></div>
        <div className="flex items-center justify-between rounded-2xl border-2 border-slate-100 p-3"><span className="font-black">购买数量</span><div className="flex items-center gap-3"><button aria-label="减少数量" onClick={() => setQuantity(Math.max(1, quantity - 1))} className="focus-ring h-12 w-12 rounded-full bg-slate-100 text-2xl font-black">−</button><span className="w-8 text-center text-2xl font-black">{quantity}</span><button aria-label="增加数量" onClick={() => setQuantity(Math.min(product.stock, quantity + 1))} className="focus-ring h-12 w-12 rounded-full bg-emerald-100 text-2xl font-black text-emerald-800">＋</button></div></div>
        {message && <p className="rounded-2xl bg-emerald-100 p-3 font-bold text-emerald-900">{message}</p>}
        {error && <p role="alert" className="rounded-2xl bg-red-50 p-3 font-bold text-red-800">{error}</p>}
        <LargeButton onClick={addAndGo} className="w-full bg-emerald-700 text-white">加入购物车，去确认</LargeButton>
        <SupportEntry />
      </div>
    </article>
  </div>;
}

"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProductCard from "@/components/ProductCard";
import LargeButton from "@/components/LargeButton";
import SupportEntry from "@/components/SupportEntry";
import AssistantPanel from "@/components/AssistantPanel";
import { api, type Product } from "@/lib/api";

export default function HomePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<{ id: string; name: string }[]>([]);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadProducts = useCallback(async (category: string, search: string) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (category) params.set("category_id", category);
      if (search) params.set("q", search);
      setProducts(await api.products(params.toString()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "商品暂时无法加载。");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api.categories().then(setCategories).catch(() => setError("分类暂时无法加载。"));
    void loadProducts("", "");
  }, [loadProducts]);

  function search(event: React.FormEvent) {
    event.preventDefault();
    setQuery(input.trim());
    void loadProducts(selected, input.trim());
  }

  function assistantSearch(searchText: string) {
    setInput(searchText);
    setQuery(searchText);
    setSelected("");
    void loadProducts("", searchText);
  }

  return (
    <div className="space-y-12">
      <section className="grid gap-8 border-b border-stone pb-10 lg:grid-cols-[1.4fr_.6fr] lg:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ember">日常用品 · 简单购物</p>
          <h1 className="mt-4 max-w-3xl text-4xl font-medium leading-[1.12] tracking-[-0.04em] text-ink sm:text-6xl">简单买，放心收</h1>
          <p className="mt-5 max-w-2xl text-xl leading-relaxed text-muted">精选日常用品，字大、步骤少。您可以直接搜索，也可以说出想买的东西。</p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <a className="focus-ring inline-flex min-h-[52px] items-center justify-center rounded-md bg-ink px-5 py-3 text-lg font-semibold text-cream hover:bg-forest" href="#products">开始选购 <span className="ml-3 text-amber">→</span></a>
            <Link className="focus-ring inline-flex min-h-[52px] items-center justify-center rounded-md bg-linen px-5 py-3 text-lg font-semibold text-ink hover:bg-bone" href="/family">家人协助 <span className="ml-3 text-amber">→</span></Link>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 border-t border-stone pt-5 text-base text-muted lg:mb-2 lg:grid-cols-1">
          <div><p className="text-2xl font-medium text-ink">字大</p><p className="mt-1">看得清每一步</p></div>
          <div><p className="text-2xl font-medium text-ink">有人帮</p><p className="mt-1">家人可以一起处理</p></div>
        </div>
      </section>

      <AssistantPanel onSearch={assistantSearch} onOpenOrders={() => { window.location.href = "/orders"; }} />

      <section id="products" className="scroll-mt-6 space-y-6">
        <div className="flex flex-col gap-3 border-b border-stone pb-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ember">商品目录</p>
            <h2 className="mt-2 text-3xl font-medium tracking-[-0.03em] text-ink">今天想买什么？</h2>
          </div>
          <Link className="focus-ring inline-flex min-h-12 items-center rounded-md text-lg font-semibold text-forest underline decoration-stone underline-offset-4 hover:text-ink" href="/cart">查看购物车 <span className="ml-2 text-amber">→</span></Link>
        </div>

        <form onSubmit={search} className="flex flex-col gap-3 sm:flex-row">
          <label className="sr-only" htmlFor="search">搜索商品</label>
          <input id="search" value={input} onChange={(event) => setInput(event.target.value)} placeholder="想买什么？例如：牛奶" className="focus-ring min-h-[52px] min-w-0 flex-1 rounded-md border border-stone bg-bone px-4 text-lg text-ink outline-none placeholder:text-muted focus:border-ink" />
          <LargeButton type="submit" className="bg-ink text-cream hover:bg-forest">搜索 <span className="ml-2 text-amber">→</span></LargeButton>
        </form>

        <div className="flex flex-wrap gap-2" aria-label="商品分类">
          <button type="button" onClick={() => { setSelected(""); setQuery(""); setInput(""); void loadProducts("", ""); }} className={`focus-ring rounded-md border px-4 py-3 text-lg font-semibold ${!selected ? "border-ink bg-ink text-cream" : "border-stone bg-linen text-ink hover:border-ink"}`}>全部</button>
          {categories.map((category) => <button type="button" key={category.id} onClick={() => { setSelected(category.id); void loadProducts(category.id, query); }} className={`focus-ring rounded-md border px-4 py-3 text-lg font-semibold ${selected === category.id ? "border-ink bg-ink text-cream" : "border-stone bg-linen text-ink hover:border-ink"}`}>{category.name}</button>)}
        </div>

        {error && <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-4 font-semibold text-red-900">{error}</p>}
        {loading ? <p className="rounded-md border border-stone bg-bone p-8 text-center text-lg font-semibold">正在为您准备商品……</p> : products.length ? <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">{products.map((product) => <ProductCard key={product.id} product={product} />)}</div> : <p className="rounded-md border border-stone bg-bone p-8 text-center text-lg font-semibold">没有找到合适的商品，换个说法试试。</p>}
      </section>

      <SupportEntry />
    </div>
  );
}

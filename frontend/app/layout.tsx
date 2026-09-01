import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "老人购物｜简单买，放心收",
  description: "老人友好的精选商品购物原型",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="min-h-screen bg-cream">
          <header className="border-b border-stone bg-cream">
            <div className="mx-auto max-w-6xl px-5 py-4 sm:flex sm:items-center sm:justify-between">
              <Link className="focus-ring inline-flex min-h-12 items-center text-2xl font-medium tracking-tight text-ink" href="/">老人购物</Link>
              <nav className="mt-3 grid grid-cols-3 gap-2 text-base font-medium sm:mt-0 sm:flex sm:items-center">
                <Link className="focus-ring rounded-md px-3 py-3 text-center text-ink hover:bg-linen" href="/orders">我的订单</Link>
                <Link className="focus-ring rounded-md px-3 py-3 text-center text-ink hover:bg-linen" href="/family">家人协助</Link>
                <Link className="focus-ring rounded-md px-3 py-3 text-center text-forest hover:bg-linen" href="/support">联系客服</Link>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-5 pb-16 pt-8">{children}</main>
        </div>
      </body>
    </html>
  );
}

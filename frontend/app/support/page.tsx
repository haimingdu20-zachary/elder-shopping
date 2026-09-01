"use client";

import Link from "next/link";

export default function SupportPage() {
  return <div className="space-y-5"><Link href="/" className="focus-ring inline-flex rounded-xl px-2 py-1 font-black text-emerald-800">← 回到首页</Link><h1 className="text-3xl font-black">联系客服</h1><section className="space-y-3 rounded-3xl bg-white p-6 shadow-soft"><p className="text-xl font-black">您好，人工客服入口正在准备中。</p><p>如果您在演示中遇到问题，可以把页面截图或问题告诉产品团队。正式版本会提供人工客服帮助。</p><button className="focus-ring min-h-12 w-full rounded-2xl bg-orange-100 px-5 py-3 font-black text-orange-900" type="button" onClick={() => window.alert("这是原型提示：人工客服将在后续阶段接入。")}>查看客服说明</button></section></div>;
}

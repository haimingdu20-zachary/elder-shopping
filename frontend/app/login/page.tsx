"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import LargeButton from "@/components/LargeButton";
import { saveSession } from "@/lib/auth";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!code.trim()) return;
    setBusy(true);
    setError("");
    try {
      const session = await api.login(code.trim());
      saveSession(session);
      router.replace(session.user.role === "family" ? "/family" : "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录暂时无法完成，请稍后再试。");
    } finally {
      setBusy(false);
    }
  }

  return <div className="mx-auto max-w-xl space-y-7 py-10"><div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-ember">安全进入</p><h1 className="mt-3 text-4xl font-medium tracking-[-0.04em] text-ink">请输入家人给您的邀请码</h1><p className="mt-4 text-lg leading-relaxed text-muted">登录后，订单、地址和购物车只会显示当前账号自己的内容。</p></div><form onSubmit={submit} className="space-y-4 rounded-md border border-stone bg-bone p-6 shadow-soft"><label className="block text-lg font-semibold text-ink" htmlFor="invite-code">邀请码<input id="invite-code" autoComplete="one-time-code" value={code} onChange={(event) => setCode(event.target.value)} className="focus-ring mt-2 min-h-[56px] w-full rounded-md border border-stone bg-cream px-4 text-xl text-ink outline-none focus:border-ink" placeholder="请输入邀请码" /></label>{error && <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-4 font-semibold text-red-900">{error}</p>}<LargeButton type="submit" disabled={busy || !code.trim()} className="w-full bg-ink text-cream hover:bg-forest">{busy ? "正在登录……" : "进入老人购物"}</LargeButton></form><p className="text-base leading-relaxed text-muted">邀请码由平台或家人线下提供。不要把邀请码发在公开群聊中。</p></div>;
}

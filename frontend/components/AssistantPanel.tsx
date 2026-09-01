"use client";

import { useEffect, useRef, useState } from "react";
import LargeButton from "@/components/LargeButton";
import { api, type AssistantHistoryMessage, type AssistantResult } from "@/lib/api";

type SpeechResult = { results: ArrayLike<ArrayLike<{ transcript: string }>> };
type SpeechRecognitionLike = { lang: string; interimResults: boolean; continuous: boolean; onresult: ((event: SpeechResult) => void) | null; onerror: (() => void) | null; onend: (() => void) | null; start: () => void; stop: () => void };
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

export default function AssistantPanel({ onSearch, onOpenOrders }: { onSearch: (query: string) => void; onOpenOrders: () => void }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<AssistantResult | null>(null);
  const [listening, setListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const historyRef = useRef<AssistantHistoryMessage[]>([]);

  useEffect(() => {
    const speechWindow = window as Window & { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor };
    setSpeechSupported(Boolean(speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition));
    return () => { recognitionRef.current?.stop(); };
  }, []);

  function toggleListening() {
    const speechWindow = window as Window & { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor };
    if (listening) { recognitionRef.current?.stop(); setListening(false); return; }
    const Constructor = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Constructor) { setError("当前浏览器不支持语音，请直接输入文字。"); return; }
    const recognition = new Constructor();
    recognition.lang = "zh-CN";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => { const transcript = event.results[0]?.[0]?.transcript ?? ""; setText(transcript); setListening(false); };
    recognition.onerror = () => { setError("没有听清，请再试一次，也可以直接输入文字。"); setListening(false); };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    setError("");
    setListening(true);
    recognition.start();
  }

  async function submit(event?: React.FormEvent, overrideText?: string) {
    event?.preventDefault();
    const submittedText = (overrideText ?? text).trim();
    if (!submittedText) return;
    setBusy(true);
    setError("");
    try {
      if (!conversationIdRef.current) conversationIdRef.current = crypto.randomUUID();
      const nextResult = await api.assistantChat(submittedText, "demo-elder", historyRef.current, conversationIdRef.current);
      setResult(nextResult);
      const nextHistory: AssistantHistoryMessage[] = [...historyRef.current, { role: "user", content: submittedText }, { role: "assistant", content: nextResult.reply }];
      historyRef.current = nextHistory.slice(-8);
      if (nextResult.action?.type === "product_search" && nextResult.action.query) onSearch(nextResult.action.query);
      if (["orders", "after_sale_entry", "family_payment_entry"].includes(nextResult.action?.type ?? "")) onOpenOrders();
    } catch (err) { setError(err instanceof Error ? err.message : "助手暂时无法回应，请直接使用页面按钮。"); }
    finally { setBusy(false); }
  }

  return (
    <section aria-label="语音和文字助手" className="space-y-5 rounded-md border border-stone bg-bone p-5 shadow-soft sm:p-7">
      <div className="flex flex-col gap-2 border-b border-stone pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-ember">需要帮忙？</p><h2 className="mt-2 text-2xl font-medium tracking-[-0.03em] text-ink">告诉我您想买什么</h2></div>
        <p className="text-base text-muted">可以输入，也可以说话</p>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
        <label className="sr-only" htmlFor="assistant-input">输入给助手的话</label>
        <input id="assistant-input" value={text} onChange={(event) => setText(event.target.value)} placeholder="例如：帮我找牛奶" className="focus-ring min-h-[52px] min-w-0 flex-1 rounded-md border border-stone bg-cream px-4 text-lg text-ink outline-none placeholder:text-muted focus:border-ink" />
        <LargeButton type="submit" disabled={busy || !text.trim()} className="bg-ink text-cream hover:bg-forest">{busy ? "处理中……" : "发送"}</LargeButton>
      </form>
      <LargeButton type="button" onClick={toggleListening} className={`w-full border border-stone ${listening ? "bg-amber text-cream" : "bg-linen text-ink hover:bg-cream"}`}>{listening ? "正在听，请说话……" : speechSupported ? "点击说话" : "浏览器不支持语音，请直接输入"}</LargeButton>
      {error && <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-4 font-semibold text-red-900">{error}</p>}
      {result && <div className="space-y-3 border-t border-stone pt-4"><p className="text-lg font-semibold text-ink">{result.reply}</p><p className="text-sm text-muted">处理方式：{result.provider === "deepseek" ? `智能助手${result.model ? ` · ${result.model}` : ""}` : result.provider === "rules_fallback" ? "规则兜底（智能助手暂时不可用）" : "演示规则"}</p>{result.action?.type === "knowledge_search" && result.action.sources && result.action.sources.length > 0 && <p className="text-sm text-muted">参考说明：{result.action.sources.map((source) => source.title).join("、")}</p>}{result.needs_confirmation && <p className="text-base font-semibold text-amber-900">这是需要您确认的操作，请按照页面提示继续。</p>}<div className="flex flex-wrap gap-2">{result.suggestions.map((suggestion) => <button key={suggestion} type="button" onClick={() => { setText(suggestion); void submit(undefined, suggestion); }} className="focus-ring rounded-md border border-stone bg-linen px-3 py-3 text-base font-semibold text-ink hover:border-ink">{suggestion}</button>)}</div></div>}
    </section>
  );
}

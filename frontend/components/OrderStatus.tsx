const tone: Record<string, string> = { pending_payment: "bg-amber-100 text-amber-900", paid_pending_shipment: "bg-blue-100 text-blue-900", shipping: "bg-blue-100 text-blue-900", delivered: "bg-emerald-100 text-emerald-900", completed: "bg-slate-100 text-slate-800", after_sale: "bg-violet-100 text-violet-900" };

export default function OrderStatus({ status, label }: { status: string; label: string }) {
  return <span className={`inline-flex rounded-full px-3 py-1 text-base font-black ${tone[status] ?? "bg-slate-100 text-slate-800"}`}>{label}</span>;
}


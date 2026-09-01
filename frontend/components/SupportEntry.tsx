import Link from "next/link";

export default function SupportEntry() {
  return <Link href="/support" className="focus-ring block rounded-md border border-amber bg-linen px-4 py-4 text-center font-semibold text-ink hover:bg-bone">需要帮助？联系客服 <span className="text-amber">→</span></Link>;
}

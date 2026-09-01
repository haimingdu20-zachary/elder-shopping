"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clearSession, getSession } from "@/lib/auth";

export default function SessionControls() {
  const router = useRouter();
  const [name, setName] = useState("");

  useEffect(() => setName(getSession()?.user.display_name ?? ""), []);

  if (!name) return null;
  return <div className="col-span-3 flex items-center justify-end gap-3 text-sm text-muted sm:col-span-1"><span>{name}</span><button type="button" className="focus-ring rounded-md px-2 py-2 underline underline-offset-4" onClick={() => { clearSession(); router.replace("/login"); }}>退出</button></div>;
}

"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getSession } from "@/lib/auth";

const authRequired = process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_AUTH_REQUIRED !== "false";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(!authRequired || pathname === "/login");

  useEffect(() => {
    if (!authRequired || pathname === "/login") {
      setReady(true);
      return;
    }
    if (!getSession()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [pathname, router]);

  if (!ready && authRequired) return <div className="rounded-md border border-stone bg-bone p-8 text-center text-lg font-semibold">正在检查登录状态……</div>;
  return <>{children}</>;
}

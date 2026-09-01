import Link from "next/link";
import Image from "next/image";
import type { Product } from "@/lib/api";

export default function ProductCard({ product }: { product: Product }) {
  return (
    <Link href={`/products/${product.id}`} className="focus-ring group block rounded-md border border-stone bg-bone p-4 shadow-soft transition-colors hover:border-ink">
      <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-md bg-linen"><Image className="object-cover transition-transform duration-300 group-hover:scale-[1.02]" src={product.image_url} alt={product.name} fill sizes="(max-width: 640px) 50vw, 33vw" /></div>
      <div className="px-1 pb-1 pt-3">
        <h3 className="line-clamp-2 min-h-14 text-xl font-medium tracking-tight text-ink">{product.name}</h3>
        <p className="mt-2 text-base text-muted">{product.estimated_delivery_text}</p>
        <div className="mt-3 flex items-end justify-between gap-2"><strong className="text-2xl font-semibold text-forest">¥{product.price}</strong><span className="text-base text-muted">/{product.unit_label}</span></div>
      </div>
    </Link>
  );
}

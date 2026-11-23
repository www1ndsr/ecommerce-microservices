import { Link } from "react-router-dom";
import type { Product } from "../types/api";
import { formatPrice } from "../utils/format";

export function ProductCard({ product }: { product: Product }) {
  return (
    <article className="product-card group overflow-hidden rounded-[1.6rem] border border-[#e8ebe5] bg-white shadow-card transition duration-300 hover:-translate-y-1 hover:border-[#c8d7c8] hover:shadow-xl">
      <Link to={`/products/${product.id}`} className="block">
        <div className="product-card-media relative flex aspect-[4/3] items-center justify-center overflow-hidden">
          {product.image_url ? (
            <img src={product.image_url} alt={product.name} className="h-full w-full object-contain p-8 transition duration-700 ease-out group-hover:scale-110" />
          ) : (
            <div className="grid h-24 w-24 place-items-center rounded-[2rem] bg-white/80 text-brand-600 shadow-card transition duration-500 group-hover:rotate-[-5deg] group-hover:scale-105">
              <svg viewBox="0 0 48 48" className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="1.4">
                <rect x="7" y="9" width="34" height="25" rx="3" />
                <path d="M17 40h14M24 34v6M13 15h22" strokeLinecap="round" />
              </svg>
            </div>
          )}
          <span className="absolute left-4 top-4 inline-flex items-center gap-1.5 rounded-full border border-white/70 bg-white/90 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.12em] text-[#365b43] shadow-sm backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />{product.stock > 0 ? "В наличии" : "Нет в наличии"}
          </span>
          <span className="absolute bottom-4 right-4 grid h-10 w-10 translate-y-2 place-items-center rounded-full bg-white text-ink opacity-0 shadow-lg transition duration-300 group-hover:translate-y-0 group-hover:opacity-100" aria-hidden="true">↗</span>
        </div>
        <div className="p-5">
          <div className="flex items-start justify-between gap-3">
            <h2 className="line-clamp-1 text-base font-semibold tracking-[-.02em] text-ink">{product.name}</h2>
            <span className="shrink-0 rounded-full bg-[#edf3eb] px-3 py-1 text-sm font-bold text-[#31583e]">{formatPrice(product.price)}</span>
          </div>
          <p className="mt-2 line-clamp-2 min-h-10 text-[13px] leading-5 text-muted">{product.description || "Подробности о товаре"}</p>
          <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-xs">
            <span className="text-muted">Осталось {product.stock} шт.</span>
            <span className="font-semibold text-brand-700 transition group-hover:translate-x-1">Подробнее <span aria-hidden="true">→</span></span>
          </div>
        </div>
      </Link>
    </article>
  );
}

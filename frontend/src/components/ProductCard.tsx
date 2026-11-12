import { Link } from "react-router-dom";
import type { Product } from "../types/api";
import { formatPrice } from "../utils/format";

export function ProductCard({ product }: { product: Product }) {
  return (
    <article className="group overflow-hidden rounded-3xl border border-slate-100 bg-white shadow-card transition duration-300 hover:-translate-y-1 hover:shadow-xl">
      <Link to={`/products/${product.id}`} className="block">
        <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 via-white to-brand-50">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="h-full w-full object-contain p-8 transition duration-500 group-hover:scale-105"
            />
          ) : (
            <div className="grid h-24 w-24 place-items-center rounded-[2rem] bg-white/80 text-brand-500 shadow-card">
              <svg viewBox="0 0 48 48" className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="1.4">
                <rect x="7" y="9" width="34" height="25" rx="3" />
                <path d="M17 40h14M24 34v6M13 15h22" strokeLinecap="round" />
              </svg>
            </div>
          )}
          <span className="absolute left-4 top-4 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-slate-600">
            {product.stock > 0 ? "В наличии" : "Нет в наличии"}
          </span>
        </div>
        <div className="p-5">
          <div className="flex items-start justify-between gap-3">
            <h2 className="line-clamp-1 text-base font-semibold text-ink">
              {product.name}
            </h2>
            <span className="shrink-0 text-sm font-semibold text-brand-700">
              {formatPrice(product.price)}
            </span>
          </div>
          <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 text-muted">
            {product.description || "Подробности о товаре"}
          </p>
          <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-sm">
            <span className="text-muted">Остаток: {product.stock}</span>
            <span className="font-semibold text-brand-700 transition group-hover:translate-x-1">
              Подробнее <span aria-hidden="true">→</span>
            </span>
          </div>
        </div>
      </Link>
    </article>
  );
}

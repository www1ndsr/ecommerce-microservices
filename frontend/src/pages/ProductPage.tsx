import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { addCartItem } from "../api/cart";
import { getProduct } from "../api/products";
import { ErrorNotice, LoadingState } from "../components/LoadingState";
import { useAuth } from "../context/AuthContext";
import type { Product } from "../types/api";
import { getErrorMessage } from "../utils/errors";
import { formatPrice } from "../utils/format";

export function ProductPage() {
  const { id } = useParams();
  const productId = Number(id);
  const { identity } = useAuth();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    if (!Number.isInteger(productId) || productId < 1) {
      setError("Некорректный идентификатор товара.");
      setIsLoading(false);
      return;
    }
    getProduct(productId)
      .then((result) => {
        if (active) setProduct(result);
      })
      .catch((cause: unknown) => {
        if (active) setError(getErrorMessage(cause));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [productId]);

  const addToCart = async () => {
    if (!identity) {
      navigate("/login");
      return;
    }
    if (!product) return;
    setIsAdding(true);
    setNotice("");
    try {
      await addCartItem(product.id, 1);
      setNotice("Товар добавлен в корзину.");
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setIsAdding(false);
    }
  };

  if (isLoading) return <LoadingState label="Загружаем товар…" />;
  if (error && !product) {
    return (
      <div className="space-y-5">
        <Link to="/" className="text-sm font-semibold text-brand-700">← В каталог</Link>
        <ErrorNotice message={error} />
      </div>
    );
  }
  if (!product) return null;

  return (
    <div className="page-enter">
      <div className="flex items-center gap-2 text-xs text-muted"><Link to="/" className="transition hover:text-brand-700">Nord</Link><span>/</span><span>Каталог</span><span>/</span><span className="max-w-48 truncate text-ink">{product.name}</span></div>
      <section className="mt-5 grid overflow-hidden rounded-[2rem] border border-[#e8ebe5] bg-white shadow-card lg:grid-cols-[1.05fr_.95fr]">
        <div className="soft-grid relative flex min-h-80 items-center justify-center overflow-hidden bg-[#eef2eb] p-10 sm:min-h-[34rem]">
          <span className="absolute left-6 top-6 inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/80 px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[.16em] text-[#365b43] backdrop-blur"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Nord selection</span>
          {product.image_url ? (
            <img src={product.image_url} alt={product.name} className="relative max-h-[28rem] max-w-full object-contain drop-shadow-[0_24px_30px_rgba(28,43,34,.14)] transition duration-700 hover:scale-[1.04]" />
          ) : (
            <div className="grid h-40 w-40 place-items-center rounded-[3rem] bg-white text-brand-500 shadow-card">
              <svg viewBox="0 0 48 48" className="h-20 w-20" fill="none" stroke="currentColor" strokeWidth="1.2">
                <rect x="7" y="9" width="34" height="25" rx="3" />
                <path d="M17 40h14M24 34v6M13 15h22" strokeLinecap="round" />
              </svg>
            </div>
          )}
        </div>
        <div className="flex flex-col p-7 sm:p-10 lg:p-12">
          <span className="w-fit rounded-full bg-[#edf3eb] px-3.5 py-1.5 text-[10px] font-bold uppercase tracking-[.14em] text-brand-700">
            {product.stock > 0 ? `В наличии · ${product.stock} шт.` : "Нет в наличии"}
          </span>
          <h1 className="mt-5 font-serif text-4xl font-medium leading-tight tracking-[-.035em] text-ink sm:text-5xl">
            {product.name}
          </h1>
          <p className="mt-5 leading-7 text-muted">
            {product.description || "Описание товара пока не добавлено."}
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3 border-y border-slate-100 py-5 text-xs text-muted">
            <span className="flex items-center gap-2"><span className="text-brand-700">✓</span> Проверенное качество</span>
            <span className="flex items-center gap-2"><span className="text-brand-700">↗</span> Удобная доставка</span>
          </div>
          <div className="mt-auto pt-7">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Цена</p>
            <p className="mt-1 font-serif text-4xl font-medium tracking-tight text-ink">{formatPrice(product.price)}</p>
            {error && <div className="mt-4"><ErrorNotice message={error} /></div>}
            {notice && (
              <p role="status" className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {notice}
              </p>
            )}
            <button
              disabled={product.stock < 1 || isAdding}
              onClick={addToCart}
              className="button-primary mt-6 w-full sm:w-auto sm:px-8"
            >
              {isAdding ? "Добавляем…" : "Добавить в корзину"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

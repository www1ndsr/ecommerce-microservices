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
    <div>
      <Link to="/" className="text-sm font-semibold text-brand-700 hover:text-brand-600">
        ← Вернуться в каталог
      </Link>
      <section className="mt-5 grid overflow-hidden rounded-[2rem] border border-slate-100 bg-white shadow-card lg:grid-cols-2">
        <div className="flex min-h-80 items-center justify-center bg-gradient-to-br from-slate-100 via-white to-brand-50 p-10 sm:min-h-[32rem]">
          {product.image_url ? (
            <img src={product.image_url} alt={product.name} className="max-h-[28rem] max-w-full object-contain" />
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
          <span className="w-fit rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
            {product.stock > 0 ? `В наличии · ${product.stock} шт.` : "Нет в наличии"}
          </span>
          <h1 className="mt-5 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            {product.name}
          </h1>
          <p className="mt-5 leading-7 text-muted">
            {product.description || "Описание товара пока не добавлено."}
          </p>
          <div className="mt-auto pt-10">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Цена</p>
            <p className="mt-1 text-3xl font-bold text-ink">{formatPrice(product.price)}</p>
            {error && <div className="mt-4"><ErrorNotice message={error} /></div>}
            {notice && (
              <p role="status" className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {notice}
              </p>
            )}
            <button
              disabled={product.stock < 1 || isAdding}
              onClick={addToCart}
              className="button-primary mt-6 w-full sm:w-auto"
            >
              {isAdding ? "Добавляем…" : "Добавить в корзину"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

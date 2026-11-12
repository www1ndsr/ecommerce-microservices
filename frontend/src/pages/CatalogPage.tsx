import { useEffect, useState, type FormEvent } from "react";
import { getProducts } from "../api/products";
import { ProductCard } from "../components/ProductCard";
import { EmptyState, ErrorNotice, LoadingState } from "../components/LoadingState";
import type { Product } from "../types/api";
import { getErrorMessage } from "../utils/errors";

export function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError("");
    getProducts({ q: query || undefined, limit: 100 })
      .then((result) => {
        if (active) setProducts(result);
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
  }, [query]);

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setQuery(search.trim());
  };

  const availableProducts = products.filter((product) => product.stock > 0);

  return (
    <div>
      <section className="relative mb-10 overflow-hidden rounded-[2rem] bg-ink px-6 py-10 text-white sm:px-10 sm:py-14">
        <div className="absolute -right-12 -top-24 h-72 w-72 rounded-full bg-brand-500/30 blur-3xl" />
        <div className="absolute -bottom-36 right-1/3 h-64 w-64 rounded-full bg-cyan-400/10 blur-3xl" />
        <div className="relative max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-200">
            Подборка Nord
          </p>
          <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-5xl">
            Технологии, которые работают на вас.
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
            Практичная техника для дома, работы и новых идей — с понятным выбором и удобным заказом.
          </p>
          <form onSubmit={submitSearch} className="mt-8 flex max-w-lg gap-2 rounded-2xl bg-white p-2 shadow-xl">
            <input
              aria-label="Поиск товаров"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="min-w-0 flex-1 bg-transparent px-3 text-sm text-ink outline-none placeholder:text-slate-400"
              placeholder="Найти товар…"
            />
            <button type="submit" className="button-primary">
              Найти
            </button>
          </form>
        </div>
      </section>

      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-600">
            Каталог
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-ink">
            Выбрано для вас
          </h2>
        </div>
        {!isLoading && !error && (
          <span className="text-sm text-muted">
            {availableProducts.length} товаров в наличии
          </span>
        )}
      </div>

      {error && <ErrorNotice message={error} />}
      {isLoading ? (
        <LoadingState label="Загружаем каталог…" />
      ) : !error && availableProducts.length === 0 ? (
        <EmptyState
          title={query ? "Ничего не найдено" : "Пока нет товаров в наличии"}
          description={
            query
              ? "Попробуйте изменить поисковый запрос."
              : "Каталог обновится, когда товары появятся."
          }
          action={
            query ? (
              <button
                className="button-secondary"
                onClick={() => {
                  setSearch("");
                  setQuery("");
                }}
              >
                Сбросить поиск
              </button>
            ) : undefined
          }
        />
      ) : (
        !error && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {availableProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )
      )}
    </div>
  );
}

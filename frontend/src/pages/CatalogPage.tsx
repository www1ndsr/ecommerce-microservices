import { useEffect, useMemo, useState, type FormEvent } from "react";
import { getProducts } from "../api/products";
import { ProductCard } from "../components/ProductCard";
import { EmptyState, ErrorNotice, LoadingState } from "../components/LoadingState";
import type { Product } from "../types/api";
import { getErrorMessage } from "../utils/errors";

type SortMode = "featured" | "price-low" | "price-high";

function Sparkle() {
  return <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true"><path d="m12 2 1.9 7.1L21 12l-7.1 2.9L12 22l-2.9-7.1L2 12l7.1-2.9L12 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /></svg>;
}

export function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("featured");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError("");
    getProducts({ q: query || undefined, limit: 100 })
      .then((result) => { if (active) setProducts(result); })
      .catch((cause: unknown) => { if (active) setError(getErrorMessage(cause)); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [query]);

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setQuery(search.trim());
  };

  const availableProducts = useMemo(() => {
    const items = products.filter((product) => product.stock > 0);
    if (sort === "price-low") return [...items].sort((a, b) => a.price - b.price);
    if (sort === "price-high") return [...items].sort((a, b) => b.price - a.price);
    return items;
  }, [products, sort]);

  return (
    <div className="page-enter">
      <section className="hero-panel mb-12 min-h-[440px] px-6 py-9 text-white sm:px-10 sm:py-12 lg:flex lg:items-center lg:px-16">
        <div className="hero-orbit" aria-hidden="true" />
        <div className="hero-device" aria-hidden="true"><div className="hero-device-screen" /></div>
        <div className="relative z-10 max-w-2xl pb-40 sm:pb-48 lg:pb-0">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.07] px-3.5 py-2 text-[11px] font-semibold uppercase tracking-[.2em] text-emerald-100">
            <Sparkle /> Nord · коллекция 2026
          </div>
          <h1 className="mt-6 max-w-xl font-serif text-[2.6rem] font-medium leading-[1.05] tracking-[-.045em] sm:text-6xl">
            Технологии для <span className="text-emerald-200">вашего</span> ритма.
          </h1>
          <p className="mt-5 max-w-md text-sm leading-6 text-white/70 sm:text-base sm:leading-7">
            Продуманные вещи для дома, работы и всего, что происходит между ними.
            Выбирайте то, что делает каждый день проще.
          </p>
          <form onSubmit={submitSearch} className="mt-8 flex max-w-[490px] items-center gap-2 rounded-2xl border border-white/50 bg-white p-1.5 shadow-2xl shadow-black/20 transition focus-within:ring-4 focus-within:ring-emerald-200/20">
            <svg viewBox="0 0 24 24" fill="none" className="ml-3 h-5 w-5 shrink-0 text-slate-400" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8" stroke="currentColor" strokeWidth="1.7" /><path d="m16 16 4.5 4.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>
            <input
              aria-label="Поиск товаров"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="min-w-0 flex-1 bg-transparent px-2 py-3 text-sm text-ink outline-none placeholder:text-slate-400"
              placeholder="Что вы ищете?"
            />
            <button type="submit" className="button-primary rounded-xl px-5 py-3">Найти</button>
          </form>
          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-white/55">
            <span>Популярное:</span>
            {["наушники", "для дома", "умные устройства"].map((term) => (
              <button key={term} onClick={() => { setSearch(term); setQuery(term); }} className="border-b border-white/20 pb-0.5 transition hover:border-emerald-200 hover:text-emerald-100">{term}</button>
            ))}
          </div>
        </div>
        <div className="absolute bottom-7 left-6 right-6 z-10 flex items-center gap-3 text-[10px] uppercase tracking-[.18em] text-white/45 sm:left-10 sm:right-auto lg:bottom-9 lg:left-16">
          <span className="h-px w-8 bg-emerald-200/70" /> Сделано для жизни, а не для витрины
        </div>
      </section>

      <section className="mb-12 grid gap-3 sm:grid-cols-3">
        {[
          { icon: "✳", title: "Только полезное", text: "Ничего лишнего в подборке" },
          { icon: "↗", title: "Легко выбрать", text: "Понятные описания и цены" },
          { icon: "⌂", title: "Для каждого дня", text: "Техника, которая работает" },
        ].map((feature) => (
          <div key={feature.title} className="flex items-center gap-4 rounded-2xl border border-[#e8ebe5] bg-white/70 px-5 py-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#edf3eb] text-lg text-[#3f6b50]">{feature.icon}</span>
            <div><p className="text-sm font-semibold text-ink">{feature.title}</p><p className="mt-0.5 text-xs text-muted">{feature.text}</p></div>
          </div>
        ))}
      </section>

      <section id="catalog">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[.2em] text-brand-700"><Sparkle /> Подборка Nord</p>
            <h2 className="mt-2 font-serif text-3xl font-medium tracking-tight text-ink sm:text-4xl">Хороший выбор на каждый день</h2>
          </div>
          <span className="text-sm text-muted">Вещи, к которым быстро привыкаешь</span>
        </div>

        <div className="catalog-toolbar mb-6 flex flex-wrap items-center justify-between gap-3 p-3 sm:px-5">
          <div className="flex items-center gap-2 text-sm text-ink">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-[#edf3eb] text-[#3f6b50]">✳</span>
            <span className="font-medium">Каталог</span>
            {!isLoading && !error && <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-muted">{availableProducts.length}</span>}
          </div>
          <label className="flex items-center gap-2 text-xs font-medium text-muted">
            Сортировка
            <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-brand-500">
              <option value="featured">В рекомендуемом порядке</option>
              <option value="price-low">Сначала дешевле</option>
              <option value="price-high">Сначала дороже</option>
            </select>
          </label>
        </div>

        {error && <ErrorNotice message={error} />}
        {isLoading ? <LoadingState label="Подбираем для вас…" /> : !error && availableProducts.length === 0 ? (
          <EmptyState
            title={query ? "Ничего не нашлось" : "Пока нет товаров в наличии"}
            description={query ? "Попробуйте другой запрос — возможно, нужная вещь уже здесь." : "Загляните чуть позже — подборка скоро обновится."}
            action={query ? <button className="button-secondary" onClick={() => { setSearch(""); setQuery(""); }}>Показать весь каталог</button> : undefined}
          />
        ) : !error && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {availableProducts.map((product) => <ProductCard key={product.id} product={product} />)}
          </div>
        )}
      </section>
    </div>
  );
}

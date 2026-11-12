import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { addCartItem, getCart, removeCartItem } from "../api/cart";
import { createOrder } from "../api/orders";
import { EmptyState, ErrorNotice, LoadingState } from "../components/LoadingState";
import type { Cart } from "../types/api";
import { getErrorMessage } from "../utils/errors";
import { formatItemCount, formatPrice } from "../utils/format";

export function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [busyProduct, setBusyProduct] = useState<number | null>(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const refresh = async () => {
    const result = await getCart();
    setCart(result);
  };

  useEffect(() => {
    let active = true;
    getCart()
      .then((result) => {
        if (active) setCart(result);
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
  }, []);

  const changeQuantity = async (productId: number, current: number, next: number) => {
    if (next < 1 || next > 99 || next === current) return;
    setBusyProduct(productId);
    setError("");
    try {
      if (next > current) {
        setCart(await addCartItem(productId, next - current));
      } else {
        await removeCartItem(productId);
        try {
          setCart(await addCartItem(productId, next));
        } catch (cause) {
          try {
            setCart(await addCartItem(productId, current));
          } catch {
            await refresh();
          }
          throw cause;
        }
      }
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setBusyProduct(null);
    }
  };

  const remove = async (productId: number) => {
    setBusyProduct(productId);
    setError("");
    try {
      setCart(await removeCartItem(productId));
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setBusyProduct(null);
    }
  };

  const checkout = async () => {
    setIsCheckingOut(true);
    setError("");
    try {
      const order = await createOrder();
      window.dispatchEvent(new Event("cart:updated"));
      navigate(`/orders/${order.id}`);
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setIsCheckingOut(false);
    }
  };

  if (isLoading) return <LoadingState label="Загружаем корзину…" />;
  if (error && !cart) return <ErrorNotice message={error} />;
  if (!cart || cart.items.length === 0) {
    return (
      <EmptyState
        title="Корзина пока пуста"
        description="Добавьте товары из каталога — здесь появится ваш заказ."
        action={<Link to="/" className="button-primary">Перейти в каталог</Link>}
      />
    );
  }

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-600">Покупки</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Ваша корзина</h1>
      <p className="mt-2 text-sm text-muted">
        {formatItemCount(cart.items.length)} · количество можно изменить перед оформлением.
      </p>
      {error && <div className="mt-5"><ErrorNotice message={error} /></div>}

      <div className="mt-7 grid gap-6 lg:grid-cols-[1fr_340px]">
        <section className="space-y-3">
          {cart.items.map((item) => (
            <article key={item.product_id} className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-100 bg-white p-4 shadow-card sm:flex-nowrap sm:p-5">
              <div className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-600">
                <span className="text-xl">N</span>
              </div>
              <div className="min-w-0 flex-1">
                <Link to={`/products/${item.product_id}`} className="font-semibold text-ink hover:text-brand-700">
                  {item.name}
                </Link>
                <p className="mt-1 text-sm text-muted">{formatPrice(item.price)} за единицу</p>
              </div>
              <div className="flex items-center rounded-full border border-slate-200">
                <button
                  aria-label={`Уменьшить количество ${item.name}`}
                  disabled={busyProduct === item.product_id || item.quantity <= 1}
                  onClick={() => changeQuantity(item.product_id, item.quantity, item.quantity - 1)}
                  className="grid h-9 w-9 place-items-center text-lg text-slate-500 hover:text-ink disabled:opacity-40"
                >
                  −
                </button>
                <span className="w-8 text-center text-sm font-semibold text-ink">{item.quantity}</span>
                <button
                  aria-label={`Увеличить количество ${item.name}`}
                  disabled={busyProduct === item.product_id || item.quantity >= 99}
                  onClick={() => changeQuantity(item.product_id, item.quantity, item.quantity + 1)}
                  className="grid h-9 w-9 place-items-center text-lg text-slate-500 hover:text-ink disabled:opacity-40"
                >
                  +
                </button>
              </div>
              <div className="w-24 text-right text-sm font-semibold text-ink">
                {formatPrice(item.price * item.quantity)}
              </div>
              <button
                disabled={busyProduct === item.product_id}
                onClick={() => remove(item.product_id)}
                className="rounded-full px-2 py-1 text-xs font-medium text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
              >
                Удалить
              </button>
            </article>
          ))}
        </section>

        <aside className="h-fit rounded-3xl border border-slate-100 bg-white p-6 shadow-card">
          <h2 className="text-lg font-semibold text-ink">Итого</h2>
          <div className="mt-5 flex justify-between text-sm text-muted">
            <span>Товары</span>
            <span>{formatPrice(cart.total)}</span>
          </div>
          <div className="my-5 border-t border-slate-100" />
          <div className="flex justify-between font-semibold text-ink">
            <span>Сумма заказа</span>
            <span>{formatPrice(cart.total)}</span>
          </div>
          <button
            disabled={isCheckingOut}
            onClick={checkout}
            className="button-primary mt-6 w-full"
          >
            {isCheckingOut ? "Оформляем…" : "Оформить заказ"}
          </button>
          <p className="mt-3 text-center text-xs leading-5 text-muted">
            Заказ создаётся с текущими товарами в корзине.
          </p>
        </aside>
      </div>
    </div>
  );
}

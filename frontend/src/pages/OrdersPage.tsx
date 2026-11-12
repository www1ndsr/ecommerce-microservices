import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getOrders } from "../api/orders";
import { EmptyState, ErrorNotice, LoadingState } from "../components/LoadingState";
import { StatusBadge } from "../components/StatusBadge";
import type { Order } from "../types/api";
import { getErrorMessage } from "../utils/errors";
import { formatDate, formatItemCount, formatPrice } from "../utils/format";

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getOrders()
      .then((result) => {
        if (active) setOrders(result);
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

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-600">Покупки</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Мои заказы</h1>
      <p className="mt-2 text-sm text-muted">История и актуальный статус ваших заказов.</p>
      {error && <div className="mt-6"><ErrorNotice message={error} /></div>}
      {isLoading ? (
        <LoadingState label="Загружаем заказы…" />
      ) : !error && orders.length === 0 ? (
        <div className="mt-7">
          <EmptyState
            title="Заказов пока нет"
            description="Когда вы оформите первую покупку, она появится здесь."
            action={<Link to="/" className="button-primary">Открыть каталог</Link>}
          />
        </div>
      ) : (
        !error && (
          <div className="mt-7 space-y-3">
            {orders.map((order) => (
              <Link
                key={order.id}
                to={`/orders/${order.id}`}
                className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-100 bg-white p-5 shadow-card transition hover:border-brand-100 hover:shadow-lg"
              >
                <div>
                  <p className="font-semibold text-ink">Заказ №{order.id}</p>
                  <p className="mt-1 text-sm text-muted">{formatDate(order.created_at)}</p>
                  <p className="mt-2 text-xs text-muted">
                    {formatItemCount(order.items.length)}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="font-semibold text-ink">{formatPrice(order.total)}</span>
                  <StatusBadge status={order.status} />
                </div>
              </Link>
            ))}
          </div>
        )
      )}
    </div>
  );
}

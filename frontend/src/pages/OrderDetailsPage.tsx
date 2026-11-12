import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { cancelOrder, getOrder } from "../api/orders";
import { getPayment } from "../api/payments";
import { ErrorNotice, LoadingState } from "../components/LoadingState";
import { StatusBadge } from "../components/StatusBadge";
import type { Order, Payment } from "../types/api";
import { getErrorMessage, isNotFound } from "../utils/errors";
import { formatDate, formatPrice } from "../utils/format";

export function OrderDetailsPage() {
  const { id } = useParams();
  const orderId = Number(id);
  const [order, setOrder] = useState<Order | null>(null);
  const [payment, setPayment] = useState<Payment | null>(null);
  const [paymentPending, setPaymentPending] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isCancelling, setIsCancelling] = useState(false);
  const [error, setError] = useState("");

  const loadOrder = useCallback(async () => {
    if (!Number.isInteger(orderId) || orderId < 1) {
      setError("Некорректный идентификатор заказа.");
      setIsLoading(false);
      return;
    }
    setError("");
    try {
      const result = await getOrder(orderId);
      setOrder(result);
      try {
        setPayment(await getPayment(orderId));
        setPaymentPending(false);
      } catch (cause) {
        if (isNotFound(cause)) {
          setPayment(null);
          setPaymentPending(true);
        } else {
          throw cause;
        }
      }
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setIsLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    void loadOrder();
  }, [loadOrder]);

  const onCancel = async () => {
    setIsCancelling(true);
    setError("");
    try {
      setOrder(await cancelOrder(orderId));
      await loadOrder();
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setIsCancelling(false);
    }
  };

  if (isLoading) return <LoadingState label="Загружаем заказ…" />;
  if (error && !order) {
    return (
      <div className="space-y-5">
        <Link to="/orders" className="text-sm font-semibold text-brand-700">← К заказам</Link>
        <ErrorNotice message={error} />
      </div>
    );
  }
  if (!order) return null;

  return (
    <div>
      <Link to="/orders" className="text-sm font-semibold text-brand-700 hover:text-brand-600">
        ← Все заказы
      </Link>
      <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-600">Информация о покупке</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Заказ №{order.id}</h1>
          <p className="mt-2 text-sm text-muted">Создан {formatDate(order.created_at)}</p>
        </div>
        <StatusBadge status={order.status} />
      </div>

      {error && <div className="mt-5"><ErrorNotice message={error} /></div>}

      <div className="mt-7 grid gap-6 lg:grid-cols-[1fr_330px]">
        <section className="rounded-3xl border border-slate-100 bg-white p-5 shadow-card sm:p-7">
          <h2 className="text-lg font-semibold text-ink">Состав заказа</h2>
          <div className="mt-4 divide-y divide-slate-100">
            {order.items.map((item, index) => (
              <div key={`${item.product_id}-${index}`} className="flex flex-wrap items-center justify-between gap-3 py-4">
                <div>
                  <p className="font-medium text-ink">{item.name}</p>
                  <p className="mt-1 text-sm text-muted">
                    {formatPrice(item.price)} × {item.quantity}
                  </p>
                </div>
                <p className="font-semibold text-ink">{formatPrice(item.price * item.quantity)}</p>
              </div>
            ))}
          </div>
          <div className="mt-3 flex justify-between border-t border-slate-100 pt-5 font-semibold text-ink">
            <span>Итого</span>
            <span>{formatPrice(order.total)}</span>
          </div>
        </section>

        <aside className="h-fit rounded-3xl border border-slate-100 bg-white p-6 shadow-card">
          <h2 className="text-lg font-semibold text-ink">Оплата</h2>
          {payment ? (
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-muted">Статус</span>
                <StatusBadge status={payment.status} />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted">Сумма</span>
                <span className="font-medium text-ink">{formatPrice(payment.amount)}</span>
              </div>
              {payment.reason && (
                <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
                  {payment.reason}
                </p>
              )}
            </div>
          ) : (
            <p className="mt-3 text-sm leading-6 text-muted">
              {paymentPending
                ? "Платёж ещё обрабатывается или пока не зарегистрирован."
                : "Информация об оплате недоступна."}
            </p>
          )}
          {paymentPending && (
            <button onClick={() => void loadOrder()} className="button-secondary mt-4 w-full">
              Обновить статус
            </button>
          )}
          {order.status === "PENDING" && (
            <button
              disabled={isCancelling}
              onClick={onCancel}
              className="mt-5 w-full rounded-full border border-red-100 px-5 py-3 text-sm font-semibold text-red-600 transition hover:bg-red-50 disabled:opacity-50"
            >
              {isCancelling ? "Отменяем…" : "Отменить заказ"}
            </button>
          )}
        </aside>
      </div>
    </div>
  );
}

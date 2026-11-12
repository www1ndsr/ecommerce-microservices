export function formatPrice(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatItemCount(count: number): string {
  const plural = new Intl.PluralRules("ru").select(count);
  const label =
    plural === "one" ? "позиция" : plural === "few" ? "позиции" : "позиций";
  return `${count} ${label}`;
}

export function formatStatus(status: string): string {
  const labels: Record<string, string> = {
    PENDING: "Ожидает оплаты",
    PAID: "Оплачен",
    PAYMENT_FAILED: "Оплата не прошла",
    CANCELLED: "Отменён",
    COMPLETED: "Оплачен",
    FAILED: "Не прошла",
  };
  return labels[status] ?? status.replaceAll("_", " ");
}

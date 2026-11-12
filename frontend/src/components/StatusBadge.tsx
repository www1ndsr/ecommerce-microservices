import { formatStatus } from "../utils/format";

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase();
  const tone =
    normalized === "PAID" || normalized === "COMPLETED"
      ? "bg-emerald-50 text-emerald-700"
      : normalized === "PAYMENT_FAILED" || normalized === "FAILED"
        ? "bg-red-50 text-red-700"
        : normalized === "CANCELLED"
          ? "bg-slate-100 text-slate-600"
          : "bg-amber-50 text-amber-700";

  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${tone}`}>
      {formatStatus(status)}
    </span>
  );
}

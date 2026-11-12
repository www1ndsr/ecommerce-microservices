import api from "./client";
import type { Payment } from "../types/api";

export async function getPayment(orderId: number): Promise<Payment> {
  const response = await api.get<Payment>(`/api/payments/order/${orderId}`);
  return response.data;
}

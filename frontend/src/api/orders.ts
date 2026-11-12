import api from "./client";
import type { Order } from "../types/api";

export async function getOrders(): Promise<Order[]> {
  const response = await api.get<Order[]>("/api/orders");
  return response.data;
}

export async function getOrder(orderId: number): Promise<Order> {
  const response = await api.get<Order>(`/api/orders/${orderId}`);
  return response.data;
}

export async function createOrder(): Promise<Order> {
  const response = await api.post<Order>("/api/orders");
  return response.data;
}

export async function cancelOrder(orderId: number): Promise<Order> {
  const response = await api.post<Order>(`/api/orders/${orderId}/cancel`);
  return response.data;
}

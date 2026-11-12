import api from "./client";
import type { Cart } from "../types/api";

export async function getCart(): Promise<Cart> {
  const response = await api.get<Cart>("/api/cart");
  return response.data;
}

export async function addCartItem(
  productId: number,
  quantity: number,
): Promise<Cart> {
  const response = await api.post<Cart>("/api/cart/items", {
    product_id: productId,
    quantity,
  });
  window.dispatchEvent(new Event("cart:updated"));
  return response.data;
}

export async function removeCartItem(productId: number): Promise<Cart> {
  const response = await api.delete<Cart>(`/api/cart/items/${productId}`);
  window.dispatchEvent(new Event("cart:updated"));
  return response.data;
}

export async function clearCart(): Promise<void> {
  await api.delete("/api/cart");
  window.dispatchEvent(new Event("cart:updated"));
}

import api from "./client";
import type { Product } from "../types/api";

export interface ProductQuery {
  q?: string;
  limit?: number;
  offset?: number;
}

export async function getProducts(query: ProductQuery = {}): Promise<Product[]> {
  const response = await api.get<Product[]>("/api/products", { params: query });
  return response.data;
}

export async function getProduct(productId: number): Promise<Product> {
  const response = await api.get<Product>(`/api/products/${productId}`);
  return response.data;
}

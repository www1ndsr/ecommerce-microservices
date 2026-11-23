import api from "./client";
import type { Product } from "../types/api";

export interface ProductQuery {
  q?: string;
  limit?: number;
  offset?: number;
}

export async function getProducts(query: ProductQuery = {}): Promise<Product[]> {
  const response = await api.get<Product[]>("/api/products", { params: query });
  const stocks = await getStocks(response.data.map((product) => product.id));
  return response.data.map((product) => ({ ...product, stock: stocks.get(product.id) ?? 0 }));
}

export async function getProduct(productId: number): Promise<Product> {
  const response = await api.get<Product>(`/api/products/${productId}`);
  const stocks = await getStocks([productId]);
  return { ...response.data, stock: stocks.get(productId) ?? 0 };
}

async function getStocks(productIds: number[]): Promise<Map<number, number>> {
  if (productIds.length === 0) return new Map();
  const response = await api.get<Array<{ product_id: number; available: number }>>(
    "/api/inventory",
    { params: { product_ids: productIds.join(",") } },
  );
  return new Map(response.data.map((item) => [item.product_id, item.available]));
}

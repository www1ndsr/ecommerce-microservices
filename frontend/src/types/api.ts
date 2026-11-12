export interface Credentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AuthIdentity {
  user_id: number;
  role: string;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  stock: number;
  image_url: string;
}

export interface CartItem {
  product_id: number;
  name: string;
  price: number;
  quantity: number;
}

export interface Cart {
  items: CartItem[];
  total: number;
}

export interface OrderItem {
  product_id: number;
  name: string;
  price: number;
  quantity: number;
}

export interface Order {
  id: number;
  user_id: number;
  total: number;
  status: string;
  created_at: string;
  items: OrderItem[];
}

export interface Payment {
  id: number;
  order_id: number;
  user_id: number;
  amount: number;
  status: string;
  reason: string;
  created_at: string;
}

export interface UserProfile {
  user_id: number;
  full_name: string;
  phone: string;
  address: string;
}

import api from "./client";
import type { AuthIdentity, Credentials, TokenResponse } from "../types/api";

export async function register(credentials: Credentials): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/api/auth/register", credentials);
  return response.data;
}

export async function login(credentials: Credentials): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/api/auth/login", credentials);
  return response.data;
}

export async function verifyToken(): Promise<AuthIdentity> {
  const response = await api.get<AuthIdentity>("/api/auth/verify");
  return response.data;
}

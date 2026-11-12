import api from "./client";
import type { UserProfile } from "../types/api";

export type ProfileUpdate = Omit<UserProfile, "user_id">;

export async function getProfile(): Promise<UserProfile> {
  const response = await api.get<UserProfile>("/api/users/me");
  return response.data;
}

export async function updateProfile(data: ProfileUpdate): Promise<UserProfile> {
  const response = await api.put<UserProfile>("/api/users/me", data);
  return response.data;
}

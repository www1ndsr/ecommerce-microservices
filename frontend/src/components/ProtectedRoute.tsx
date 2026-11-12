import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LoadingState } from "./LoadingState";

export function ProtectedRoute() {
  const { identity, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <LoadingState />;
  if (!identity) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

import type { ReactNode } from "react";
import { Navigate } from "react-router";
import { loadUser } from "../lib/storage";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  if (!loadUser()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

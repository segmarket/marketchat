import { Navigate } from "react-router";
import { useAuth } from "../context/AuthContext";

export default function AppRootRedirect() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return <Navigate to={isAuthenticated ? "/admin" : "/login"} replace />;
}

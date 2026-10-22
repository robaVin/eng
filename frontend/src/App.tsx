import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Results from "./pages/Results";
import Review from "./pages/Review";
import TestSetup from "./pages/TestSetup";
import Upload from "./pages/Upload";

type AuthState = { loading: boolean; authed: boolean; aiConfigured: boolean };

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ loading: true, authed: false, aiConfigured: false });
  const location = useLocation();

  const refresh = async () => {
    try {
      const me = await api.me();
      setAuth({ loading: false, authed: me.authenticated, aiConfigured: me.ai_configured });
    } catch {
      setAuth({ loading: false, authed: false, aiConfigured: false });
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  if (auth.loading) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Loading…</div>;
  }

  if (!auth.authed) {
    if (location.pathname !== "/login") return <Navigate to="/login" replace />;
    return <Login onLoggedIn={refresh} />;
  }

  return (
    <Layout aiConfigured={auth.aiConfigured} onLogout={refresh}>
      <Routes>
        <Route path="/" element={<Results />} />
        <Route path="/setup" element={<TestSetup />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/review/:id" element={<Review aiConfigured={auth.aiConfigured} />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

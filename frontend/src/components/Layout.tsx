import { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { api } from "../api";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-lg text-sm font-medium ${
    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
  }`;

export default function Layout({
  children,
  aiConfigured,
  onLogout,
}: {
  children: ReactNode;
  aiConfigured: boolean;
  onLogout: () => void;
}) {
  const navigate = useNavigate();
  const logout = async () => {
    await api.logout();
    onLogout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
          <div className="mr-4 flex items-center gap-2 font-semibold text-slate-800">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-500 text-white">✓</span>
            <span className="hidden sm:inline">Test Grading</span>
          </div>
          <nav className="flex flex-1 flex-wrap gap-1">
            <NavLink to="/" end className={linkClass}>
              Results
            </NavLink>
            <NavLink to="/setup" className={linkClass}>
              Test Setup
            </NavLink>
            <NavLink to="/upload" className={linkClass}>
              Upload Work
            </NavLink>
          </nav>
          {!aiConfigured && (
            <span className="badge bg-amber-100 text-amber-700" title="Set ANTHROPIC_API_KEY in the backend .env">
              AI key not set
            </span>
          )}
          <button onClick={logout} className="btn-ghost ml-2">
            Log out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}

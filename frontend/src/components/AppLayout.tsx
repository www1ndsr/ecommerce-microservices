import { Outlet } from "react-router-dom";
import { Header } from "./Header";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-canvas">
      <Header />
      <main className="mx-auto min-h-[calc(100vh-150px)] max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-6 text-xs text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <span>© {new Date().getFullYear()} Nord. Техника для повседневной жизни.</span>
          <span>Безопасные покупки · Удобная доставка</span>
        </div>
      </footer>
    </div>
  );
}

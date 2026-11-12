import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { getCart } from "../api/cart";
import { useAuth } from "../context/AuthContext";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-3 py-2 text-sm font-medium transition ${
    isActive
      ? "bg-brand-50 text-brand-700"
      : "text-slate-600 hover:bg-slate-100 hover:text-ink"
  }`;

export function Header() {
  const { identity, signOut } = useAuth();
  const [cartCount, setCartCount] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    let refreshVersion = 0;
    const refresh = () => {
      const currentVersion = ++refreshVersion;
      if (!identity) {
        setCartCount(0);
        return;
      }
      getCart()
        .then((cart) => {
          if (active && currentVersion === refreshVersion) {
            setCartCount(cart.items.reduce((sum, item) => sum + item.quantity, 0));
          }
        })
        .catch(() => {
          if (active && currentVersion === refreshVersion) setCartCount(0);
        });
    };
    refresh();
    window.addEventListener("cart:updated", refresh);
    return () => {
      active = false;
      window.removeEventListener("cart:updated", refresh);
    };
  }, [identity]);

  const logout = () => {
    signOut();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-ink text-sm font-bold text-white">
            N
          </span>
          <span>
            <span className="block text-lg font-bold tracking-tight text-ink">
              nord
            </span>
            <span className="hidden text-[10px] font-semibold uppercase tracking-[0.18em] text-muted sm:block">
              everyday technology
            </span>
          </span>
        </Link>

        <nav className="order-3 flex w-full items-center gap-1 overflow-x-auto sm:order-none sm:w-auto">
          <NavLink to="/" end className={linkClass}>
            Каталог
          </NavLink>
          {identity && (
            <>
              <NavLink to="/orders" className={linkClass}>
                Заказы
              </NavLink>
              <NavLink to="/profile" className={linkClass}>
                Профиль
              </NavLink>
            </>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {identity ? (
            <>
              <Link
                to="/cart"
                aria-label={`Корзина, товаров: ${cartCount}`}
                className="relative grid h-10 w-10 place-items-center rounded-full border border-slate-200 text-ink transition hover:border-brand-100 hover:bg-brand-50"
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M3 4h2l2.2 10.1a2 2 0 0 0 2 1.6h8.2a2 2 0 0 0 1.9-1.4L21 8H6" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="10" cy="20" r="1" />
                  <circle cx="18" cy="20" r="1" />
                </svg>
                {cartCount > 0 && (
                  <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-brand-600 px-1 text-[10px] font-bold text-white">
                    {cartCount > 99 ? "99+" : cartCount}
                  </span>
                )}
              </Link>
              <button onClick={logout} className="button-secondary hidden sm:inline-flex">
                Выйти
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="button-secondary hidden sm:inline-flex">
                Войти
              </Link>
              <Link to="/register" className="button-primary">
                Создать аккаунт
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

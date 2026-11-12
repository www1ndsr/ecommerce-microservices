import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../utils/errors";
import { ErrorNotice } from "./LoadingState";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const isRegister = mode === "register";
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const redirectTo =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ??
    "/";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      if (isRegister) await signUp({ email, password });
      else await signIn({ email, password });
      navigate(redirectTo, { replace: true });
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto grid min-h-[65vh] max-w-5xl overflow-hidden rounded-[2rem] border border-slate-100 bg-white shadow-card lg:grid-cols-[1fr_0.85fr]">
      <div className="p-7 sm:p-10 lg:p-12">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand-600">
          Nord account
        </p>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          {isRegister ? "Создайте аккаунт" : "С возвращением"}
        </h1>
        <p className="mt-3 max-w-md text-sm leading-6 text-muted">
          {isRegister
            ? "Зарегистрируйтесь, чтобы сохранять корзину и отслеживать заказы."
            : "Войдите, чтобы продолжить покупки и посмотреть ваши заказы."}
        </p>

        <form onSubmit={submit} className="mt-8 space-y-5">
          {error && <ErrorNotice message={error} />}
          <label className="field-label">
            Электронная почта
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="field-input"
              placeholder="you@example.com"
            />
          </label>
          <label className="field-label">
            Пароль
            <input
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              required
              minLength={6}
              maxLength={72}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="field-input"
              placeholder="Не менее 6 символов"
            />
          </label>
          <button type="submit" disabled={isSubmitting} className="button-primary w-full">
            {isSubmitting
              ? "Пожалуйста, подождите…"
              : isRegister
                ? "Создать аккаунт"
                : "Войти"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          {isRegister ? "Уже есть аккаунт?" : "Впервые у нас?"}{" "}
          <Link
            to={isRegister ? "/login" : "/register"}
            className="font-semibold text-brand-700 hover:text-brand-600"
          >
            {isRegister ? "Войти" : "Зарегистрироваться"}
          </Link>
        </p>
      </div>

      <div className="relative hidden overflow-hidden bg-ink p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-brand-500/30 blur-3xl" />
        <div className="absolute -bottom-24 -left-20 h-72 w-72 rounded-full bg-cyan-400/20 blur-3xl" />
        <div className="relative">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-white/10 text-lg font-bold">
            N
          </div>
          <h2 className="mt-12 max-w-sm text-3xl font-semibold leading-tight">
            Хорошие вещи делают каждый день немного лучше.
          </h2>
          <p className="mt-4 max-w-sm text-sm leading-6 text-slate-300">
            Подборка техники, которая сочетает продуманный дизайн и полезные функции.
          </p>
        </div>
        <div className="relative flex gap-2 text-xs text-slate-300">
          <span className="rounded-full border border-white/15 px-3 py-1.5">Техника</span>
          <span className="rounded-full border border-white/15 px-3 py-1.5">Комфорт</span>
          <span className="rounded-full border border-white/15 px-3 py-1.5">Nord</span>
        </div>
      </div>
    </div>
  );
}

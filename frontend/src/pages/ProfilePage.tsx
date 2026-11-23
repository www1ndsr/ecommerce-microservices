import { useEffect, useState, type FormEvent } from "react";
import { getProfile, updateProfile, type ProfileUpdate } from "../api/users";
import { ErrorNotice, LoadingState } from "../components/LoadingState";
import type { UserProfile } from "../types/api";
import { getErrorMessage } from "../utils/errors";

const emptyProfile: ProfileUpdate = {
  full_name: "",
  phone: "",
  address: "",
};

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [form, setForm] = useState<ProfileUpdate>(emptyProfile);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    getProfile()
      .then((result) => {
        if (active) {
          setProfile(result);
          setForm({
            full_name: result.full_name,
            phone: result.phone,
            address: result.address,
          });
        }
      })
      .catch((cause: unknown) => {
        if (active) setError(getErrorMessage(cause));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setNotice("");
    setIsSaving(true);
    try {
      const result = await updateProfile(form);
      setProfile(result);
      setNotice("Изменения сохранены.");
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) return <LoadingState label="Загружаем профиль…" />;
  if (error && !profile) return <ErrorNotice message={error} />;

  const updateField = (field: keyof ProfileUpdate, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  return (
    <div className="page-enter mx-auto max-w-3xl">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-600">Аккаунт</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Мой профиль</h1>
      <p className="mt-2 text-sm text-muted">
        Данные профиля помогают оформлять покупки удобнее.
      </p>
      <form onSubmit={submit} className="mt-7 rounded-3xl border border-[#e8ebe5] bg-white p-6 shadow-card sm:p-8">
        {error && <div className="mb-5"><ErrorNotice message={error} /></div>}
        {notice && (
          <p role="status" className="mb-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {notice}
          </p>
        )}
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="field-label sm:col-span-2">
            Имя
            <input
              value={form.full_name}
              maxLength={200}
              onChange={(event) => updateField("full_name", event.target.value)}
              className="field-input"
              placeholder="Ваше имя"
            />
          </label>
          <label className="field-label">
            Телефон
            <input
              value={form.phone}
              maxLength={30}
              onChange={(event) => updateField("phone", event.target.value)}
              className="field-input"
              placeholder="+7 (000) 000-00-00"
            />
          </label>
          <label className="field-label sm:col-span-2">
            Адрес
            <textarea
              rows={3}
              value={form.address}
              maxLength={500}
              onChange={(event) => updateField("address", event.target.value)}
              className="field-input resize-y"
              placeholder="Город, улица, дом"
            />
          </label>
        </div>
        {profile && (
          <p className="mt-5 text-xs text-muted">ID пользователя: {profile.user_id}</p>
        )}
        <button disabled={isSaving} type="submit" className="button-primary mt-6">
          {isSaving ? "Сохраняем…" : "Сохранить изменения"}
        </button>
      </form>
    </div>
  );
}

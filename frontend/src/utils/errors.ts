import axios from "axios";

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data: unknown = error.response?.data;
    if (data && typeof data === "object") {
      const body = data as { detail?: unknown; error?: unknown };
      if (typeof body.detail === "string") return body.detail;
      if (typeof body.error === "string") return body.error;
    }
    if (error.code === "ECONNABORTED") {
      return "Сервис отвечает слишком долго. Попробуйте ещё раз.";
    }
    if (!error.response) {
      return "Не удалось подключиться к API Gateway.";
    }
  }
  return "Не удалось выполнить запрос. Попробуйте ещё раз.";
}

export function isNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

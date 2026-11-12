import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as authApi from "../api/auth";
import type { AuthIdentity, Credentials } from "../types/api";
import { clearToken, getToken, saveToken } from "../utils/token";

interface AuthContextValue {
  identity: AuthIdentity | null;
  isLoading: boolean;
  signIn: (credentials: Credentials) => Promise<void>;
  signUp: (credentials: Credentials) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<AuthIdentity | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const signOut = useCallback(() => {
    clearToken();
    setIdentity(null);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let active = true;
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      return () => {
        active = false;
      };
    }

    authApi
      .verifyToken()
      .then((result) => {
        if (active) setIdentity(result);
      })
      .catch(() => {
        if (active) signOut();
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [signOut]);

  useEffect(() => {
    window.addEventListener("auth:expired", signOut);
    return () => window.removeEventListener("auth:expired", signOut);
  }, [signOut]);

  const establishSession = async (credentials: Credentials, create: boolean) => {
    const result = create
      ? await authApi.register(credentials)
      : await authApi.login(credentials);
    saveToken(result.access_token);
    try {
      const currentIdentity = await authApi.verifyToken();
      setIdentity(currentIdentity);
    } catch (error) {
      clearToken();
      throw error;
    }
  };

  const signIn = (credentials: Credentials) => establishSession(credentials, false);
  const signUp = (credentials: Credentials) => establishSession(credentials, true);

  return (
    <AuthContext.Provider
      value={{ identity, isLoading, signIn, signUp, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

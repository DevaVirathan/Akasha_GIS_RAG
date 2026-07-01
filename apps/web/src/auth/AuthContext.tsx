import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { devLogin, getMe } from "../api/client";

interface AuthState {
  token: string | null;
  email: string | null;
  isAdmin: boolean;
  loading: boolean;
  error: string | null;
  login: (email: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthState | null>(null);
const KEY = "akasha_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(KEY));
  const [email, setEmail] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Validate an existing token on load; drop it if invalid.
  useEffect(() => {
    if (!token) return;
    getMe(token)
      .then((me) => {
        setEmail(me.email);
        setIsAdmin(me.is_admin);
      })
      .catch(() => {
        localStorage.removeItem(KEY);
        setToken(null);
      });
  }, [token]);

  async function login(em: string) {
    setLoading(true);
    setError(null);
    try {
      const r = await devLogin(em.trim());
      localStorage.setItem(KEY, r.access_token);
      setToken(r.access_token);
      setEmail(r.email);
      setIsAdmin(r.is_admin);
    } catch (e: any) {
      setError(e?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem(KEY);
    setToken(null);
    setEmail(null);
    setIsAdmin(false);
  }

  return (
    <Ctx.Provider value={{ token, email, isAdmin, loading, error, login, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}

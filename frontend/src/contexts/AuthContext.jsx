import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { authApi } from "../api/authApi";

const AuthContext = createContext(null);

const TOKEN_KEY = "kpi_access_token";
const USER_KEY = "kpi_user";

export function AuthProvider({ children }) {
  /** Restore the locally cached identity while the token is validated. */
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then((data) => {
        const { access_token, ...userInfo } = data;
        localStorage.setItem(TOKEN_KEY, access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
        setUser(userInfo);
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  /** Authenticate and persist the current account for page reloads. */
  const login = useCallback(async (email, password) => {
    const data = await authApi.login(email, password);
    const { access_token, ...userInfo } = data;
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
    setUser(userInfo);
    return userInfo;
  }, []);

  /** Clear the current browser session. */
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      isAuthenticated: !!user,
      isAdmin: user?.is_admin === true,
    }),
    [user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  /** Return the authenticated application context. */
  const authContext = useContext(AuthContext);
  if (!authContext)
    throw new Error("useAuth phải được dùng trong AuthProvider");
  return authContext;
}

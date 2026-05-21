import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const SessionContext = createContext(null);

function useSessionValue() {
  const [user, setUser] = useState(undefined);

  const reload = useCallback(() => {
    return fetch("/api/me", { credentials: "same-origin" })
      .then((r) => r.json())
      .then((d) => {
        setUser(d.user ?? null);
        return d.user ?? null;
      })
      .catch(() => {
        setUser(null);
        return null;
      });
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return useMemo(
    () => ({
      user,
      loading: user === undefined,
      reload,
    }),
    [user, reload]
  );
}

export function SessionProvider({ children }) {
  const value = useSessionValue();
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const v = useContext(SessionContext);
  if (!v) throw new Error("useSession вне SessionProvider");
  return v;
}

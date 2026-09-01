export type UserSession = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: { user_id: string; role: "elder" | "family"; display_name: string };
};

const SESSION_KEY = "elder-shopping-session";

export function getSession(): UserSession | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.sessionStorage.getItem(SESSION_KEY);
    return value ? (JSON.parse(value) as UserSession) : null;
  } catch {
    return null;
  }
}

export function saveSession(session: UserSession): void {
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  window.sessionStorage.removeItem(SESSION_KEY);
}

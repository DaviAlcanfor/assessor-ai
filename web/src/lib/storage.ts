// Versionado (react-best-practices.md: "Version and Minimize localStorage Data") — sem senha,
// só o suficiente pro modo dev lembrar qual usuário aleatório "entrou" (ver protected-route.tsx).
const KEY = "assessor-ai:user:v1";

export interface StoredUser {
  user_id: string;
  nome: string;
}

export function loadUser(): StoredUser | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as StoredUser) : null;
  } catch {
    return null;
  }
}

export function saveUser(user: StoredUser): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(user));
  } catch {
    // localStorage indisponível (privado/quota) — segue sem persistir
  }
}
